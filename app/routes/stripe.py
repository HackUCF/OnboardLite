# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
import uuid

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError, MultipleResultsFound
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models.user import PaymentModel, UserModel, user_to_dict
from app.util.approve import Approve
from app.util.auth_dependencies import CurrentMember
from app.util.database import get_session
from app.util.membership_reset import MembershipReset
from app.util.settings import Settings

templates = Jinja2Templates(directory="app/templates")


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pay", tags=["API"])

if not Settings().stripe.pause_payments:
    # Set Stripe API key.
    stripe.api_key = Settings().stripe.api_key.get_secret_value()  # type: ignore[attribute-error]


@router.get("/")
async def get_root(
    request: Request,
    current_user: CurrentMember,
    session: Session = Depends(get_session),
):
    """
    Get API information.
    """
    statement = select(UserModel).where(UserModel.id == uuid.UUID(current_user["id"])).options(selectinload(UserModel.discord))  # type: ignore[bad-argument-type]
    user_data = session.exec(statement).one_or_none()
    if user_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    did_pay_dues = user_data.did_pay_dues

    user_data = user_to_dict(user_data)

    paused_payments = Settings().stripe.pause_payments
    dues_restart_soon = MembershipReset.dues_restart_soon(session)

    return templates.TemplateResponse(
        request,
        "pay.html",
        {
            "user_data": user_data,
            "did_pay_dues": did_pay_dues,
            "paused_payments": paused_payments,
            "dues_restart_soon": dues_restart_soon,
        },
    )


@router.post("/checkout")
async def create_checkout_session(
    request: Request,
    current_user: CurrentMember,
    session: Session = Depends(get_session),
):
    """Create a new Stripe checkout session."""
    if Settings().stripe.pause_payments:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payments are currently paused")

    user_data = session.exec(select(UserModel).where(UserModel.id == uuid.UUID(current_user.get("id")))).one_or_none()
    if user_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user_data.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No email associated with account")
    user_id = user_data.id
    try:
        stripe_email = user_data.email
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    "price": Settings().stripe.price_id,  # type: ignore[bad-argument-type]
                    "quantity": 1,
                },
            ],
            customer_email=stripe_email,
            mode="payment",
            success_url=Settings().stripe.url_success,  # type: ignore[bad-argument-type]
            cancel_url=Settings().stripe.url_failure,  # type: ignore[bad-argument-type]
            metadata={"user_id": str(user_id)},
        )
    except Exception as e:
        logger.exception("Error creating checkout session in stripe.py", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating checkout session")

    if not checkout_session.url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No checkout URL returned")
    return RedirectResponse(checkout_session.url, status_code=303)


@router.post("/webhook/validate")
async def webhook(request: Request, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if sig_header is None:
        logger.error("Stripe webhook missing stripe-signature header")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature header")
    event = None
    endpoint_secret = Settings().stripe.webhook_secret.get_secret_value()  # type: ignore[attribute-error]

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        # Invalid payload
        logger.error("Malformed Stripe Payload", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed payload")
    except stripe.SignatureVerificationError as e:
        # Invalid signature
        logger.error("Malformed Stripe Payload", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed payload")

    # Event Handling
    if event["type"] == "checkout.session.completed":
        # Retrieve the session. If you require line items in the response, you may include them by expanding line_items.
        checkout_session = event["data"]["object"]

        if getattr(checkout_session, "payment_status", None) == "paid":
            # Mark as paid.
            pay_dues(checkout_session, session, background_tasks)

    elif event["type"] == "checkout.session.async_payment_succeeded":
        checkout_session = event["data"]["object"]
        pay_dues(checkout_session, session, background_tasks)

    # Passed signature verification
    return {"status": "success"}


def resolve_paying_user(checkout_session, db_session):
    """
    Work out which user a checkout session belongs to.

    create_checkout_session stamps the user id into session metadata, so prefer
    that: it is exact and survives the user changing their email afterwards.
    Fall back to email only for sessions created before that was relied on.

    Read every field with getattr: Stripe hands us a StripeObject, which is not
    a dict (no ``.get()``), and missing fields raise AttributeError rather than
    returning None.
    """
    metadata = getattr(checkout_session, "metadata", None)
    raw_user_id = getattr(metadata, "user_id", None)

    if raw_user_id:
        try:
            member_id = uuid.UUID(str(raw_user_id))
        except ValueError:
            logger.warning("Stripe webhook: malformed user_id in metadata: %r", raw_user_id)
        else:
            user_data = db_session.get(UserModel, member_id)
            if user_data is not None:
                return user_data
            logger.warning("Stripe webhook: metadata user_id %s not found, falling back to email", member_id)

    customer_email = getattr(checkout_session, "customer_email", None)
    if not customer_email:
        # Blank emails are common (incomplete signups), so an empty lookup here
        # would match many rows rather than none.
        return None

    try:
        return db_session.exec(select(UserModel).where(UserModel.email == customer_email)).one_or_none()
    except MultipleResultsFound:
        logger.error("Stripe webhook: multiple users share email %s, refusing to guess", customer_email)
        return None


def pay_dues(checkout_session, db_session, background_tasks):
    session_id = getattr(checkout_session, "id", None)

    # Stripe redelivers webhooks; the session id is our idempotency key.
    if session_id is not None:
        already_recorded = db_session.exec(select(PaymentModel).where(PaymentModel.checkout_session_id == session_id)).first()
        if already_recorded is not None:
            logger.info("Stripe webhook: checkout session %s already recorded, skipping", session_id)
            return

    user_data = resolve_paying_user(checkout_session, db_session)
    if user_data is None:
        logger.error("Stripe webhook: could not resolve a user for checkout session %s", session_id)
        return

    member_id = user_data.id

    payment = PaymentModel(
        user_id=member_id,
        source="stripe",
        checkout_session_id=session_id,
        amount_cents=getattr(checkout_session, "amount_total", None),
        currency=getattr(checkout_session, "currency", None),
        customer_email=getattr(checkout_session, "customer_email", None),
    )

    # Set PAID.
    user_data.did_pay_dues = True
    db_session.add(payment)
    db_session.add(user_data)
    try:
        db_session.commit()
    except IntegrityError:
        # Another redelivery of the same session committed first.
        db_session.rollback()
        logger.info("Stripe webhook: checkout session %s recorded concurrently, skipping", session_id)
        return
    db_session.refresh(user_data)

    # Do checks to approve membership status in background.
    background_tasks.add_task(Approve.approve_member, member_id, notify_on_failure=True)

# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import stripe
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlmodel import Session, select

from app.models.user import EthicsFormModel, MembershipHistoryModel, PaymentModel, UserModel
from app.routes.stripe import build_success_url, pay_dues
from app.util.approve import Approve
from app.util.auth_dependencies import Authentication
from app.util.membership_reset import MembershipReset


def make_user(session: Session, *, email="payer@example.com", did_pay_dues=False, is_full_member=False, signtime=1, first_name="Pay", discord_id=None):
    user = UserModel(
        id=uuid.uuid4(),
        discord_id=discord_id or str(uuid.uuid4().int)[:18],
        first_name=first_name,
        surname="Er",
        email=email,
        shirt_size="M",
        did_pay_dues=did_pay_dues,
        is_full_member=is_full_member,
    )
    user.ethics_form = EthicsFormModel(signtime=signtime)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# --- pay_dues: who gets credited -------------------------------------------------


def test_pay_dues_matches_on_metadata_not_email(session: Session, checkout_session_factory):
    """The user id in session metadata wins over a mismatched customer_email."""
    payer = make_user(session, email="real@example.com")
    decoy = make_user(session, email="decoy@example.com")

    checkout = checkout_session_factory(
        customer_email="decoy@example.com",
        metadata={"user_id": str(payer.id)},
    )
    pay_dues(checkout, session, BackgroundTasks())

    session.refresh(payer)
    session.refresh(decoy)
    assert payer.did_pay_dues is True
    assert decoy.did_pay_dues is False


def test_pay_dues_falls_back_to_email_without_metadata(session: Session, checkout_session_factory):
    payer = make_user(session, email="fallback@example.com")

    checkout = checkout_session_factory(customer_email="fallback@example.com", metadata={})
    pay_dues(checkout, session, BackgroundTasks())

    session.refresh(payer)
    assert payer.did_pay_dues is True


def test_pay_dues_ignores_blank_customer_email(session: Session, checkout_session_factory):
    """Blank emails are common on incomplete signups, so must not match anyone."""
    blank_one = make_user(session, email="")
    blank_two = make_user(session, email="")

    checkout = checkout_session_factory(customer_email="", metadata={})
    pay_dues(checkout, session, BackgroundTasks())

    session.refresh(blank_one)
    session.refresh(blank_two)
    assert blank_one.did_pay_dues is False
    assert blank_two.did_pay_dues is False
    assert session.exec(select(PaymentModel)).all() == []


def test_pay_dues_records_payment_row(session: Session, checkout_session_factory):
    payer = make_user(session)

    checkout = checkout_session_factory(metadata={"user_id": str(payer.id)}, amount_total=1500, currency="usd")
    pay_dues(checkout, session, BackgroundTasks())

    payments = session.exec(select(PaymentModel)).all()
    assert len(payments) == 1
    assert payments[0].source == "stripe"
    assert payments[0].checkout_session_id == "cs_test_123"
    assert payments[0].amount_cents == 1500
    assert payments[0].user_id == payer.id


# --- pay_dues: idempotency -------------------------------------------------------


def test_pay_dues_is_idempotent_on_redelivery(session: Session, checkout_session_factory):
    """Stripe redelivers webhooks; the same session must not double-record."""
    payer = make_user(session)
    checkout = checkout_session_factory(metadata={"user_id": str(payer.id)})

    tasks_one = BackgroundTasks()
    tasks_two = BackgroundTasks()
    pay_dues(checkout, session, tasks_one)
    pay_dues(checkout, session, tasks_two)

    assert len(session.exec(select(PaymentModel)).all()) == 1
    assert len(tasks_one.tasks) == 1
    assert len(tasks_two.tasks) == 0  # second delivery queues no approval work


# --- approve_member: exactly-once notification -----------------------------------


@pytest.fixture(name="patched_approve")
def patched_approve_fixture(engine):
    """Point approve_member at the test engine and stub its outbound calls."""
    with (
        patch("app.util.approve.engine", engine),
        patch("app.util.approve.Approve.provision_infra", return_value={"username": "u", "password": "p"}),
        patch("app.util.approve.load_and_render_template", return_value="msg"),
        patch("app.util.approve.Discord") as discord,
        patch("app.util.approve.Email") as email,
    ):
        yield discord, email


def test_approve_member_sends_welcome_exactly_once(session: Session, patched_approve):
    discord, email = patched_approve
    user = make_user(session, did_pay_dues=True, is_full_member=False, signtime=1)

    assert Approve.approve_member(user.id) is True
    assert Approve.approve_member(user.id) is True

    assert email.send_email.call_count == 1
    session.refresh(user)
    assert user.is_full_member is True


def test_approve_member_survives_overlapping_calls(session: Session, engine):
    """
    Regression test for the duplicate welcome email.

    Two callers used to both pass the is_full_member check before either
    committed, so both sent. This reproduces that interleaving by re-entering
    approve_member from inside provision_infra — the exact window that used to
    be open, since promotion only committed after the send. It fails against the
    old read-then-write ordering and passes once the promotion is claimed first.
    """
    user = make_user(session, did_pay_dues=True, is_full_member=False, signtime=1)
    reentered = []

    def provision_then_reenter(member_id, user_data, reset_password=False):
        # Stand-in for the second concurrent request arriving mid-flight.
        if not reentered:
            reentered.append(True)
            Approve.approve_member(member_id)
        return {"username": "u", "password": "p"}

    with (
        patch("app.util.approve.engine", engine),
        patch("app.util.approve.Approve.provision_infra", side_effect=provision_then_reenter),
        patch("app.util.approve.load_and_render_template", return_value="msg"),
        patch("app.util.approve.Discord"),
        patch("app.util.approve.Email") as email,
    ):
        Approve.approve_member(user.id)

    assert reentered, "the overlapping call never ran; test would be vacuous"
    assert email.send_email.call_count == 1


def test_approve_member_promotes_null_is_full_member(session: Session, patched_approve):
    """is_full_member is nullable; a NULL row must still be promotable."""
    discord, email = patched_approve
    user = make_user(session, did_pay_dues=True, is_full_member=False, signtime=1)
    # Go through the model so the UUID binds correctly; SQLite stores sa.Uuid()
    # as dashless hex, so raw SQL with str(uuid) would match nothing.
    session.execute(update(UserModel).where(UserModel.id == user.id).values(is_full_member=None))
    session.commit()
    assert session.exec(select(UserModel.is_full_member).where(UserModel.id == user.id)).one() is None

    Approve.approve_member(user.id)

    assert email.send_email.call_count == 1
    session.refresh(user)
    assert user.is_full_member is True


def test_approve_member_skips_notification_when_already_promoted(session: Session, patched_approve):
    discord, email = patched_approve
    user = make_user(session, did_pay_dues=True, is_full_member=True, signtime=1)

    Approve.approve_member(user.id)

    assert email.send_email.call_count == 0


# --- the failure DM is gated -----------------------------------------------------


def test_failure_dm_suppressed_by_default(session: Session, patched_approve):
    """A profile page view must not DM the member."""
    discord, _ = patched_approve
    user = make_user(session, did_pay_dues=True, is_full_member=False, signtime=0)

    Approve.approve_member(user.id)

    assert discord.send_message.call_count == 0


def test_failure_dm_sent_when_requested(session: Session, patched_approve):
    """An admin refresh or a real payment may DM the member."""
    discord, _ = patched_approve
    user = make_user(session, did_pay_dues=True, is_full_member=False, signtime=0)

    Approve.approve_member(user.id, notify_on_failure=True)

    assert discord.send_message.call_count == 1


def test_profile_page_does_not_dm(session: Session, client: TestClient, jwt: str, engine):
    """End-to-end: loading /profile/ repeatedly sends nothing."""
    with (
        patch("app.util.approve.engine", engine),
        patch("app.util.approve.load_and_render_template", return_value="msg"),
        patch("app.util.approve.Discord") as discord,
    ):
        for _ in range(3):
            assert client.get("/profile/", cookies={"token": jwt}).status_code == 200

    assert discord.send_message.call_count == 0


# --- manual payments -------------------------------------------------------------


def test_mark_paid_records_manual_payment(session: Session, client: TestClient, admin_jwt: str, admin_user: UserModel):
    payer = make_user(session, email="manual@example.com")

    with patch("app.util.approve.Approve.approve_member", return_value=None):
        response = client.post(
            "/admin/mark_paid/",
            json={"user_id": str(payer.id), "note": "cash at meeting"},
            cookies={"token": admin_jwt},
        )

    assert response.status_code == 200

    payments = session.exec(select(PaymentModel)).all()
    assert len(payments) == 1
    assert payments[0].source == "manual"
    assert payments[0].checkout_session_id is None
    assert payments[0].recorded_by_admin_id == admin_user.id
    assert payments[0].note == "cash at meeting"

    session.refresh(payer)
    assert payer.did_pay_dues is True


def test_mark_paid_requires_admin(session: Session, client: TestClient, jwt: str):
    payer = make_user(session)

    response = client.post(
        "/admin/mark_paid/",
        json={"user_id": str(payer.id)},
        cookies={"token": jwt},
        follow_redirects=False,
    )

    assert response.status_code != 200
    assert session.exec(select(PaymentModel)).all() == []


def test_did_pay_dues_not_editable_through_generic_editor():
    """Payments must go through mark_paid so they land in the audit log."""
    from app.models.user import UserModelMutable

    assert "did_pay_dues" not in UserModelMutable.model_fields


# --- dues reset banner -----------------------------------------------------------


def test_banner_hidden_before_april(session: Session):
    assert MembershipReset.dues_restart_soon(session, datetime(2026, 3, 31, tzinfo=timezone.utc)) is False


def test_banner_shows_from_april_when_never_reset(session: Session):
    assert MembershipReset.dues_restart_soon(session, datetime(2026, 4, 1, tzinfo=timezone.utc)) is True


def test_banner_hidden_once_this_years_reset_ran(session: Session):
    user = make_user(session)
    session.add(MembershipHistoryModel(user_id=user.id, reset_date=datetime(2026, 8, 1, tzinfo=timezone.utc)))
    session.commit()

    # After the reset, stays off for the rest of that year...
    assert MembershipReset.dues_restart_soon(session, datetime(2026, 9, 1, tzinfo=timezone.utc)) is False
    # ...and comes back the following April.
    assert MembershipReset.dues_restart_soon(session, datetime(2027, 4, 1, tzinfo=timezone.utc)) is True


def test_pay_page_renders(session: Session, client: TestClient, jwt: str):
    """The banner query runs on a real request, not just in isolation."""
    response = client.get("/pay/", cookies={"token": jwt})
    assert response.status_code == 200


def test_admin_settings_page_renders(session: Session, client: TestClient, admin_jwt: str):
    response = client.get("/admin/settings/", cookies={"token": admin_jwt})
    assert response.status_code == 200
    assert "Membership Settings" in response.text


def test_payments_endpoint_lists_manual_and_stripe(session: Session, client: TestClient, admin_jwt: str, checkout_session_factory):
    payer = make_user(session, email="listed@example.com")
    pay_dues(checkout_session_factory(metadata={"user_id": str(payer.id)}), session, BackgroundTasks())

    response = client.get("/admin/payments/", cookies={"token": admin_jwt})

    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 1
    assert rows[0]["source"] == "stripe"
    assert rows[0]["member_name"] == "Pay Er"


def test_last_reset_date_derives_from_history(session: Session):
    user = make_user(session)
    assert MembershipReset.get_last_reset_date(session) is None

    session.add(MembershipHistoryModel(user_id=user.id, reset_date=datetime(2025, 8, 1, tzinfo=timezone.utc)))
    session.add(MembershipHistoryModel(user_id=user.id, reset_date=datetime(2026, 8, 1, tzinfo=timezone.utc)))
    session.commit()

    assert MembershipReset.get_last_reset_date(session).year == 2026


# --- /pay/final: reconciling on return from Stripe -------------------------------


def test_build_success_url_adds_placeholder():
    """Stripe's template token must survive URL encoding verbatim."""
    assert build_success_url("https://join.hackucf.org/pay/final") == "https://join.hackucf.org/pay/final?session_id={CHECKOUT_SESSION_ID}"


def test_build_success_url_pins_stale_configured_path():
    """
    Regression: a config still pointing at /final/ sent members to a page that
    ignores session_id, so the payment was never recorded and checkout looked
    successful. Only the origin is taken from config.
    """
    assert build_success_url("https://join.hackucf.org/final/") == "https://join.hackucf.org/pay/final?session_id={CHECKOUT_SESSION_ID}"


def test_build_success_url_keeps_scheme_and_host():
    assert build_success_url("http://localhost:8000/final/") == "http://localhost:8000/pay/final?session_id={CHECKOUT_SESSION_ID}"


def test_build_success_url_drops_stale_query():
    result = build_success_url("https://join.hackucf.org/final/?ref=email")
    assert result == "https://join.hackucf.org/pay/final?session_id={CHECKOUT_SESSION_ID}"


def test_pay_final_records_payment_when_webhook_never_fires(session: Session, client: TestClient, checkout_session_factory):
    """The outage case: member returns from Stripe, webhook never arrives."""
    payer = make_user(session)
    jwt = Authentication.create_jwt(payer)
    checkout = checkout_session_factory(id="cs_return_1", metadata={"user_id": str(payer.id)}, amount_total=1062)

    # approve_member opens its own Session(engine) against the real database;
    # TestClient runs background tasks inline, so it has to be stubbed here.
    with (
        patch("app.routes.stripe.stripe.checkout.Session.retrieve", return_value=checkout),
        patch("app.routes.stripe.Approve.approve_member") as approve,
    ):
        response = client.get("/pay/final?session_id=cs_return_1", cookies={"token": jwt})

    approve.assert_called_once()

    assert response.status_code == 200
    payments = session.exec(select(PaymentModel).where(PaymentModel.checkout_session_id == "cs_return_1")).all()
    assert len(payments) == 1
    assert payments[0].amount_cents == 1062
    session.refresh(payer)
    assert payer.did_pay_dues is True


def test_pay_final_and_webhook_produce_one_payment(session: Session, client: TestClient, checkout_session_factory):
    """Both paths processing the same session must not double-credit."""
    payer = make_user(session)
    jwt = Authentication.create_jwt(payer)
    checkout = checkout_session_factory(id="cs_race_1", metadata={"user_id": str(payer.id)})

    pay_dues(checkout, session, BackgroundTasks())
    with patch("app.routes.stripe.stripe.checkout.Session.retrieve", return_value=checkout):
        response = client.get("/pay/final?session_id=cs_race_1", cookies={"token": jwt})

    assert response.status_code == 200
    payments = session.exec(select(PaymentModel).where(PaymentModel.checkout_session_id == "cs_race_1")).all()
    assert len(payments) == 1


def test_pay_final_refuses_someone_elses_session(session: Session, client: TestClient, checkout_session_factory):
    """Session ids come from a member-controlled query string."""
    payer = make_user(session, email="payer@example.com")
    attacker = make_user(session, email="attacker@example.com", discord_id="88888888888888888")
    jwt = Authentication.create_jwt(attacker)
    checkout = checkout_session_factory(id="cs_theft_1", metadata={"user_id": str(payer.id)})

    with patch("app.routes.stripe.stripe.checkout.Session.retrieve", return_value=checkout):
        response = client.get("/pay/final?session_id=cs_theft_1", cookies={"token": jwt})

    assert response.status_code == 200
    assert session.exec(select(PaymentModel)).all() == []
    session.refresh(attacker)
    session.refresh(payer)
    assert attacker.did_pay_dues is False
    assert payer.did_pay_dues is False


def test_pay_final_ignores_unpaid_session(session: Session, client: TestClient, checkout_session_factory):
    payer = make_user(session)
    jwt = Authentication.create_jwt(payer)
    checkout = checkout_session_factory(id="cs_unpaid_1", metadata={"user_id": str(payer.id)}, payment_status="unpaid")

    with patch("app.routes.stripe.stripe.checkout.Session.retrieve", return_value=checkout):
        response = client.get("/pay/final?session_id=cs_unpaid_1", cookies={"token": jwt})

    assert response.status_code == 200
    assert session.exec(select(PaymentModel)).all() == []


def test_pay_final_renders_without_session_id(session: Session, client: TestClient):
    """The join flow lands here too, with no session_id."""
    payer = make_user(session)
    jwt = Authentication.create_jwt(payer)
    response = client.get("/pay/final", cookies={"token": jwt})
    assert response.status_code == 200


def test_pay_final_survives_stripe_being_down(session: Session, client: TestClient):
    """A Stripe outage must not break the confirmation page."""
    payer = make_user(session)
    jwt = Authentication.create_jwt(payer)

    with patch("app.routes.stripe.stripe.checkout.Session.retrieve", side_effect=stripe.APIConnectionError("down")):
        response = client.get("/pay/final?session_id=cs_down_1", cookies={"token": jwt})

    assert response.status_code == 200
    assert session.exec(select(PaymentModel)).all() == []

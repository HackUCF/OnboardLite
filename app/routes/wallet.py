# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models.info import InfoModel
from app.models.user import PublicContact, UserModel, user_to_dict
from app.util.apple_wallet import AppleWalletGenerator
from app.util.authentication import Authentication
from app.util.database import get_session
from app.util.errors import Errors
from app.util.google_wallet import GoogleWalletManager
from app.util.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/wallet",
    tags=["API", "MobileWallet"],
    responses=Errors.basic_http(),
)


# Initialize wallet managers
try:
    google_wallet_manager = GoogleWalletManager() if Settings().google_wallet.enable else None
except Exception as e:
    logger.warning(f"Failed to initialize Google Wallet manager: {e}")
    google_wallet_manager = None

try:
    apple_wallet_generator = AppleWalletGenerator()
except Exception as e:
    logger.warning(f"Failed to initialize Apple Wallet generator: {e}")
    apple_wallet_generator = None


@router.get("/")
async def get_root():
    """
    Get API information.
    """
    return InfoModel(
        name="Onboard for Mobile Wallets",
        description="Apple Wallet support.",
        credits=[
            PublicContact(
                first_name="Jonathan",
                surname="Styles",
                ops_email="jstyles@hackucf.org",
            )
        ],
    )


@router.get("/apple")
@Authentication.member
async def aapl_gen(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    session=Depends(get_session),
):
    """Generate and return an Apple Wallet pass for the authenticated user."""
    if not apple_wallet_generator:
        return Errors.generate(
            request=request,
            num=503,
            msg="Apple Wallet service is not available",
        )

    try:
        statement = select(UserModel).where(UserModel.id == uuid.UUID(user_jwt["id"])).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
        user_data = user_to_dict(session.exec(statement).one_or_none())

        pass_data = apple_wallet_generator.generate_pass(user_data)

        return Response(
            content=pass_data,
            media_type="application/vnd.apple.pkpass",
            headers={"Content-Disposition": 'attachment; filename="hackucf.pkpass"'},
        )
    except Exception as e:
        logger.error(f"Failed to generate Apple Wallet pass: {e}")
        return Errors.generate(
            request=request,
            num=500,
            msg="Failed to generate Apple Wallet pass",
        )


@router.get("/google")
@Authentication.member
async def google_gen(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    session=Depends(get_session),
):
    """Generate and redirect to Google Wallet pass for the authenticated user."""
    if not google_wallet_manager:
        return Errors.generate(
            request=request,
            num=503,
            msg="Google Wallet service is not available",
        )

    try:
        statement = select(UserModel).where(UserModel.id == uuid.UUID(user_jwt["id"])).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
        user_data = session.exec(statement).one_or_none()

        if not user_data:
            return Errors.generate(
                request=request,
                num=404,
                msg="User not found",
            )

        # Generate the Google Wallet save URL
        save_url = google_wallet_manager.create_jwt_save_url(user_data)

        return RedirectResponse(save_url)

    except Exception as e:
        logger.error(f"Failed to generate Google Wallet pass: {e}")
        return Errors.generate(
            request=request,
            num=500,
            msg="Failed to generate Google Wallet pass",
        )

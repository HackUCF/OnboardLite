# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models.info import InfoModel
from app.models.user import PublicContact, UserModel, user_to_dict
from app.util.apple_wallet import AppleWalletGenerator
from app.util.auth_dependencies import CurrentMember
from app.util.database import get_session
from app.util.google_wallet import GoogleWalletManager
from app.util.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/wallet",
    tags=["API", "MobileWallet"],
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
async def aapl_gen(
    request: Request,
    current_user: CurrentMember,
    session=Depends(get_session),
):
    """Generate and return an Apple Wallet pass for the authenticated user."""
    if not apple_wallet_generator:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Apple Wallet service is not available")

    try:
        statement = select(UserModel).where(UserModel.id == uuid.UUID(current_user["id"])).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
        user_data = user_to_dict(session.exec(statement).one_or_none())

        pass_data = apple_wallet_generator.generate_pass(user_data)

        return Response(
            content=pass_data,
            media_type="application/vnd.apple.pkpass",
            headers={"Content-Disposition": 'attachment; filename="hackucf.pkpass"'},
        )
    except Exception as e:
        logger.error(f"Failed to generate Apple Wallet pass: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate Apple Wallet pass")


@router.get("/google")
async def google_gen(
    request: Request,
    current_user: CurrentMember,
    session=Depends(get_session),
):
    """Generate and redirect to Google Wallet pass for the authenticated user."""
    if not google_wallet_manager:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google Wallet service is not available")

    try:
        statement = select(UserModel).where(UserModel.id == uuid.UUID(current_user["id"])).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
        user_data = session.exec(statement).one_or_none()

        if not user_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Generate the Google Wallet save URL
        save_url = google_wallet_manager.create_jwt_save_url(user_data)

        return RedirectResponse(save_url)
    except ValueError as err:
        logger.error(f"Failed to generate Google Wallet pass: {err}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate Google Wallet pass")

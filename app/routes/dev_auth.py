# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
import uuid

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.models.user import (
    DiscordModel,
    UserModel,
)
from app.util.authentication import Authentication
from app.util.database import get_session
from app.util.errors import Errors
from app.util.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["API"], responses=Errors.basic_http())


@router.get("/user/")
async def create_dev_user(request: Request, session: Session = Depends(get_session), sudo: bool = False):
    if request.client.host not in ["127.0.0.1", "localhost"]:
        return Errors.generate(
            request,
            403,
            "Forbidden",
            essay="This endpoint is only available on localhost.",
        )

    # Generate random user data
    user_id = uuid.uuid4()
    discord_id = str(uuid.uuid4())

    user = UserModel(id=user_id, discord_id=discord_id, sudo=sudo)

    discord_user = DiscordModel(username=f"devuser-{user_id}", email="devuser@mail.com", user_id=user_id, user=user)

    session.add(user)
    session.commit()
    session.refresh(user)

    session.add(discord_user)
    session.commit()
    session.refresh(discord_user)

    # Create JWT token for the user
    bearer = Authentication.create_jwt(user)
    rr = RedirectResponse("/profile", status_code=status.HTTP_302_FOUND)
    max_age = Settings().jwt.lifetime_sudo
    rr.set_cookie(
        key="token",
        value=bearer,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=max_age,
    )

    return rr

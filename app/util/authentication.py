# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import time
from functools import wraps
from typing import Optional

from fastapi import Request, status
from fastapi.responses import RedirectResponse
from joserfc import errors, jwt

from app.models.user import UserModel

# Import options and errors
from app.util.errors import Errors
from app.util.settings import Settings

if Settings().telemetry.enable:
    from sentry_sdk import set_user


class Authentication:
    def __init__(self):
        super(Authentication, self).__init__

    def admin(func):
        @wraps(func)
        async def wrapper(request: Request, token: Optional[str], *args, **kwargs):
            # Validate auth.
            if not token:
                return RedirectResponse(
                    "/discord/new?redir=" + request.url.path,
                    status_code=status.HTTP_302_FOUND,
                )

            try:
                user_jwt = jwt.decode(
                    token,
                    Settings().jwt.secret.get_secret_value(),
                    algorithms=Settings().jwt.algorithm,
                )
                user_jwt = user_jwt.claims
                is_admin: bool = user_jwt.get("sudo", False)
                creation_date: float = user_jwt.get("issued", -1)
                api_key: bool = user_jwt.get("api_key", False)
            except Exception as e:
                if isinstance(e, errors.BadSignatureError):
                    tr = Errors.generate(
                        request,
                        403,
                        "Invalid token provided. Please log in again (refresh the page) and try again.",
                    )
                    tr.delete_cookie(key="token")
                    return tr
                else:
                    raise  # Re-raise exceptions that are not related to token validation

            if not is_admin:
                return Errors.generate(
                    request,
                    403,
                    "You are not a sudoer.",
                    essay="If you think this is an error, please try logging in again.",
                )
            if not api_key:
                if time.time() > creation_date + Settings().jwt.lifetime_sudo:
                    return Errors.generate(
                        request,
                        403,
                        "Session not new enough to verify sudo status.",
                        essay="Unlike normal log-in, non-bot sudoer sessions only last a day. This is to ensure the security of Hack@UCF member PII. " "Simply re-log into Onboard to continue.",
                    )

            return await func(request, token, *args, **kwargs)

        return wrapper

    def member(func):
        @wraps(func)
        async def wrapper_member(
            request: Request,
            token: Optional[str],
            user_jwt: Optional[object],
            *args,
            **kwargs,
        ):
            # Validate auth.
            if not token:
                return RedirectResponse(
                    "/discord/new?redir=" + request.url.path,
                    status_code=status.HTTP_302_FOUND,
                )

            try:
                user_jwt = jwt.decode(
                    token,
                    Settings().jwt.secret.get_secret_value(),
                    algorithms=Settings().jwt.algorithm,
                )
                user_jwt = user_jwt.claims
                creation_date: float = user_jwt.get("issued", -1)
            except Exception as e:
                if isinstance(e, errors.BadSignatureError):
                    tr = Errors.generate(
                        request,
                        403,
                        "Invalid token provided. Please log in again (refresh the page) and try again.",
                    )
                    tr.delete_cookie(key="token")
                    return tr
                else:
                    raise  # Re-raise exceptions that are not related to token validation

            if time.time() > creation_date + Settings().jwt.lifetime_user:
                return Errors.generate(
                    request,
                    403,
                    "Session expired.",
                    essay="Sessions last for about fifteen weeks. You need to re-log-in between semesters.",
                )
            if Settings().telemetry.enable:
                set_user({"id": user_jwt["id"]})
            return await func(request, token, user_jwt, *args, **kwargs)

        return wrapper_member

    def create_jwt(user: UserModel):
        jwtData = {
            "discord": user.discord_id,
            "name": user.discord.username,
            "pfp": user.discord.avatar,
            "id": str(user.id),
            "sudo": user.sudo,
            "is_full_member": user.is_full_member,
            "issued": time.time(),
            "infra_email": user.infra_email,
        }
        bearer = jwt.encode(
            {"alg": Settings().jwt.algorithm},
            jwtData,
            Settings().jwt.secret.get_secret_value(),
        )
        return bearer

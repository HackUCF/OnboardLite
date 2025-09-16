# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
import os
import uuid
from typing import Optional
from urllib.parse import urlparse

from fastapi import BackgroundTasks, Cookie, Depends, FastAPI, Request, Response, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from joserfc import jwt
from requests_oauthlib import OAuth2Session
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

# Import data types
from app.models.user import (
    DiscordModel,
    EthicsFormModel,
    UserModel,
    user_to_dict,
)

# Import routes
from app.routes import admin, api, infra, stripe, wallet

# This check is a little hacky and needs to be documented in the dev environment set up
# If it's run under docker, the -e flag should set the env variable, but if its local you have to set it yourself
# Use 'export ENV=development' to set the env variable
if os.getenv("ENV") == "development":
    from app.routes import dev_auth
from app.util.approve import Approve

# Import middleware
from app.util.auth_dependencies import Authentication, CurrentMember, sign_redirect_url, verify_redirect_url
from app.util.database import get_session, init_db
from app.util.discord import Discord

# Import error handling
from app.util.errors import Errors
from app.util.forms import Forms

# Import the page rendering library
from app.util.kennelish import Kennelish

# Import options
from app.util.settings import Settings

if Settings().telemetry.enable:
    import sentry_sdk
### TODO: TEMP
# os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "0"
###

if Settings().loglevel:
    logging.basicConfig(
        level=getattr(logging, Settings().loglevel.upper()),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

logger = logging.getLogger(__name__)


# Initiate FastAPI.
app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="OnboardLite API",
        version="1.0.0",
        description="Hack@UCF's in-house membership management suite",
        routes=app.routes,
    )

    # Fix parameter type issues
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                # Fix operation IDs to ensure uniqueness
                if "operationId" in operation:
                    operation_id = operation["operationId"]
                    if operation_id.endswith("_post") and method == "get":
                        operation["operationId"] = operation_id.replace("_post", "_get")

                # Fix parameter schemas
                if "parameters" in operation:
                    for param in operation["parameters"]:
                        if "schema" in param:
                            schema = param["schema"]
                            # Fix anyOf nullable patterns
                            if "anyOf" in schema:
                                any_of = schema["anyOf"]
                                if len(any_of) == 2:
                                    string_type = None
                                    null_type = None
                                    for item in any_of:
                                        if item.get("type") == "string":
                                            string_type = item
                                        elif item.get("type") == "null":
                                            null_type = item

                                    if string_type and null_type:
                                        # Convert to nullable string
                                        param["schema"] = {"type": "string", "nullable": True, "title": schema.get("title", "")}
                                        if not param.get("required", True):
                                            param["required"] = False

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


def global_context(request: Request):
    return {
        "sentry_url": Settings().telemetry.url if Settings().telemetry.enable else None,
        "request": request,
    }


# Register the context processor with Jinja2
templates.env.globals.update(global_context=global_context)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

if Settings().telemetry.enable:
    sentry_sdk.init(
        dsn=Settings().telemetry.url,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=0.3,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=0.3,
        environment=Settings().telemetry.env,
    )

# Import endpoints from ./routes
app.include_router(api.router)
app.include_router(stripe.router)
app.include_router(admin.router)
app.include_router(wallet.router)
app.include_router(infra.router)

# This check is a little hacky and needs to be documented in the dev environment set up
# If it's run under docker, the -e flag should set the env variable, but if its local you have to set it yourself
# Use 'export ENV=development' to set the env variable
if os.getenv("ENV") == "development":
    logger.warning("loading dev endpoints")
    app.include_router(dev_auth.router)


# TODO figure out wtf this is used for
# Create the OpenStack SDK config.
# with open("clouds.yaml", "w", encoding="utf-8") as f:
#    f.write(
#        f"""clouds:
#  hackucf_infra:
#    auth:
#      auth_url: {Settings().infra.horizon}:5000
#      application_credential_id: {Settings().infra.application_credential_id}
#      application_credential_secret: {Settings().infra.application_credential_secret.get_secret_value()}
#    region_name: "hack-ucf-0"
#    interface: "public"
#    identity_api_version: 3
#    auth_type: "v3applicationcredential"
# """
#    )


"""
Render the Onboard home page.
"""


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
async def index(request: Request, token: Optional[str] = Cookie(None)):
    is_full_member = False
    is_admin = False
    user_id = None
    infra_email = None

    if token is not None:
        try:
            # Use pre-created JWT key object from settings
            user_jwt = jwt.decode(
                token,
                Settings().jwt.key_object,
                algorithms=Settings().jwt.algorithm,
            )
            user_jwt = user_jwt.claims
            is_full_member: bool = user_jwt.get("is_full_member", False)
            is_admin: bool = user_jwt.get("sudo", False)
            user_id: bool = user_jwt.get("id", None)
            infra_email: bool = user_jwt.get("infra_email", None)
        except Exception as decode_error:
            # Token decode error - invalid/expired token, treat as unauthenticated
            logger.debug(f"JWT token decode error: {decode_error}")
            is_full_member = False
            is_admin = False
            user_id = None
            infra_email = None

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "is_full_member": is_full_member,
            "is_admin": is_admin,
            "user_id": user_id,
            "infra_email": infra_email,
        },
    )


"""
Redirects to Discord for OAuth.
This is what is linked to by Onboard.
"""


@app.get("/discord/new/")
async def oauth_transformer(redir: str = None):
    if not redir:
        redir = sign_redirect_url("/join/2")

    oauth = OAuth2Session(
        Settings().discord.client_id,
        redirect_uri=Settings().discord.redirect_base,
        scope=Settings().discord.scope,
    )
    authorization_url, state = oauth.authorization_url("https://discord.com/api/oauth2/authorize")

    rr = RedirectResponse(authorization_url, status_code=302)

    if Settings().env == "dev":
        rr.set_cookie(key="redir_endpoint", value=redir, max_age=300, httponly=True, samesite="lax", secure=False)
        rr.set_cookie(key="oauth_state", value=state, max_age=300, httponly=True, samesite="lax", secure=False)
    else:
        rr.set_cookie(key="redir_endpoint", value=redir, max_age=300, httponly=True, samesite="lax", secure=True)
        rr.set_cookie(key="oauth_state", value=state, max_age=300, httponly=True, samesite="lax", secure=True)

    return rr


"""
Logs the user into Onboard via Discord OAuth and updates their Discord metadata.
This is what Discord will redirect to.
"""


@app.get("/api/oauth/")
async def oauth_transformer_new(
    request: Request,
    response: Response,
    code: str = None,
    state: str = None,
    redir_endpoint: Optional[str] = Cookie(None),
    oauth_state: Optional[str] = Cookie(None),
    session: Session = Depends(get_session),
):
    # Open redirect check
    if redir_endpoint:
        redir_url = verify_redirect_url(redir_endpoint)
    else:
        return Errors.generate(
            request,
            400,
            "Invalid Redirect Endpoint",
        )

    if not state or not oauth_state or state != oauth_state:
        return Errors.generate(
            request,
            400,
            "Invalid OAuth state",
            essay="OAuth state validation failed. This may indicate a CSRF attack.",
        )

    if code is None:
        return Errors.generate(
            request,
            401,
            "You declined Discord log-in",
            essay="We need your Discord account to log into myHack@UCF.",
        )

    # Get data from Discord
    oauth = OAuth2Session(
        Settings().discord.client_id,
        redirect_uri=Settings().discord.redirect_base,
        scope=Settings().discord.scope,
    )

    token = oauth.fetch_token(
        "https://discord.com/api/oauth2/token",
        client_id=Settings().discord.client_id,
        client_secret=Settings().discord.secret.get_secret_value(),
        # authorization_response=code
        code=code,
    )

    r = oauth.get("https://discord.com/api/users/@me")
    discordData = r.json()

    # Generate a new user ID or reuse an existing one.
    statement = select(UserModel).where(UserModel.discord_id == discordData["id"])
    user = session.exec(statement).one_or_none()

    if not user:
        if not discordData.get("verified"):
            tr = Errors.generate(
                request,
                403,
                "Discord email not verfied please try again",
            )
            return tr
        infra_email = ""
        discord_id = discordData["id"]
        Discord().join_hack_server(discord_id, token)
        user = UserModel(discord_id=discord_id, infra_email=infra_email)
        discord_data = {
            "email": discordData.get("email"),
            "mfa": discordData.get("mfa_enabled"),
            "avatar": f"https://cdn.discordapp.com/avatars/{discordData['id']}/{discordData['avatar']}.png?size=512",
            "banner": f"https://cdn.discordapp.com/banners/{discordData['id']}/{discordData['banner']}.png?size=1536",
            "color": discordData.get("accent_color"),
            "nitro": discordData.get("premium_type"),
            "locale": discordData.get("locale"),
            "username": discordData.get("username"),
            "user_id": user.id,
        }
        discord_model = DiscordModel(**discord_data)
        ethics_form = EthicsFormModel()
        user.discord = discord_model
        user.ethics_form = ethics_form
        session.add(user)
        session.commit()
        session.refresh(user)

    # Create JWT. This should be the only way to issue JWTs.
    bearer = Authentication.create_jwt(user)
    rr = RedirectResponse(redir_url, status_code=status.HTTP_302_FOUND)
    if user.sudo:
        max_age = Settings().jwt.lifetime_sudo
    else:
        max_age = Settings().jwt.lifetime_user
    if Settings().env == "dev":
        rr.set_cookie(
            key="token",
            value=bearer,
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=max_age,
        )
    else:
        rr.set_cookie(
            key="token",
            value=bearer,
            httponly=True,
            samesite="lax",
            secure=True,
            max_age=max_age,
        )
    # Clear redirect cookie.
    rr.delete_cookie("redir_endpoint")
    rr.delete_cookie("captcha")
    rr.delete_cookie("oauth_state")
    return rr


"""
Renders the landing page for the sign-up flow.
"""


@app.get("/join/")
async def join(request: Request, token: Optional[str] = Cookie(None)):
    if token is None:
        return templates.TemplateResponse("signup.html", {"request": request})
    else:
        return RedirectResponse("/join/2/", status_code=status.HTTP_302_FOUND)


"""
Renders a basic "my membership" page
"""


@app.get("/profile/")
async def profile(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: CurrentMember,
    session: Session = Depends(get_session),
):
    statement = select(UserModel).where(UserModel.id == uuid.UUID(current_user["id"])).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    user_data = user_to_dict(session.exec(statement).one_or_none())

    # Re-run approval workflow in background.
    background_tasks.add_task(Approve.approve_member, uuid.UUID(current_user.get("id")))

    return templates.TemplateResponse("profile.html", {"request": request, "user_data": user_data})


"""
Renders a Kennelish form page, complete with stylings and UI controls.
"""


@app.get("/join/{num}/")
async def forms(
    request: Request,
    current_user: CurrentMember,
    num: str,
    session: Session = Depends(get_session),
):
    if num == "1":
        return RedirectResponse("/join/", status_code=status.HTTP_302_FOUND)
    try:
        data = Forms.get_form_body(num)
    except Exception:
        return Errors.generate(
            request,
            404,
            "Form not found",
            essay="This form does not exist.",
        )

    # Get data from SqlModel

    statement = select(UserModel).where(UserModel.id == uuid.UUID(current_user.get("id"))).options(selectinload(UserModel.discord))
    user_data = session.exec(statement).one_or_none()
    # Have Kennelish parse the data.
    user_data = user_to_dict(user_data)
    body = Kennelish.parse(data, user_data)

    # return num
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "icon": current_user["pfp"],
            "user_data": user_data,
            "id": current_user["id"],
            "body": body,
        },
    )


@app.get("/final")
async def final(request: Request):
    return templates.TemplateResponse("done.html", {"request": request})


@app.get("/logout")
async def logout(request: Request):
    rr = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    rr.delete_cookie(key="token")
    return rr


@app.get("/scanner")
async def scanner(request: Request):
    """
    Scanner interface for checking member dues status.
    Touch-friendly interface that shows green/red based on QR code scan results.
    """
    return templates.TemplateResponse("scanner.html", {"request": request})


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("./app/static/favicon.ico")

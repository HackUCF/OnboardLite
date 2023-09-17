import json, re, uuid
import os
import requests

from datetime import datetime, timedelta
import time
from typing import Optional, Union

# FastAPI
from fastapi import Depends, FastAPI, HTTPException, status, Request, Response, Cookie
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from jose import JWTError, jwt
from urllib.parse import urlparse
from requests_oauthlib import OAuth2Session

import boto3
from boto3.dynamodb.conditions import Key, Attr

# Import the page rendering library
from util.kennelish import Kennelish

# Import middleware
from util.authentication import Authentication

# Import error handling
from util.errors import Errors
from util.approve import Approve

# Import options
from util.options import Options

options = Options.fetch()

# Import data types
from models.user import UserModel

# Import routes
from routes import api, stripe, admin, wallet, infra

### TODO: TEMP
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "0"
###


# Initiate FastAPI.
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import endpoints from ./routes
app.include_router(api.router)
app.include_router(stripe.router)
app.include_router(admin.router)
app.include_router(wallet.router)
app.include_router(infra.router)

# Create the OpenStack SDK config.
with open("clouds.yaml", "w", encoding="utf-8") as f:
    f.write(
        f"""clouds:
  hackucf_infra:
    auth:
      auth_url: {options.get('infra', {}).get('horizon', '')}:5000
      username: {options.get('infra', {}).get('ad', {}).get('username', '')}
      password: {options.get('infra', {}).get('ad', {}).get('password', '')}
      project_id: 464dc8d09d9a457cba2cd1efd737d538
      project_name: "admin"
      user_domain_name: "Default"
    region_name: "hack-ucf-0"
    interface: "public"
    identity_api_version: 3
"""
    )


"""
Render the Onboard home page.
"""


@app.get("/")
async def index(request: Request, token: Optional[str] = Cookie(None)):
    is_full_member = False
    is_admin = False
    user_id = None
    infra_email = None

    try:
        payload = jwt.decode(
            token,
            options.get("jwt").get("secret"),
            algorithms=options.get("jwt").get("algorithm"),
        )
        is_full_member: bool = payload.get("is_full_member", False)
        is_admin: bool = payload.get("sudo", False)
        user_id: bool = payload.get("id", None)
        infra_email: bool = payload.get("infra_email", None)
    except Exception as e:
        print(e)
        pass

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
async def oauth_transformer(redir: str = "/join/2"):
    # Open redirect check
    hostname = urlparse(redir).netloc
    print(hostname)
    if hostname != "" and hostname != options.get("http", {}).get(
        "domain", "my.hackucf.org"
    ):
        redir = "/join/2"

    oauth = OAuth2Session(
        options.get("discord").get("client_id"),
        redirect_uri=options.get("discord").get("redirect_base") + "_redir",
        scope=options.get("discord").get("scope"),
    )
    authorization_url, state = oauth.authorization_url(
        "https://discord.com/api/oauth2/authorize"
    )

    rr = RedirectResponse(authorization_url, status_code=302)

    rr.set_cookie(key="redir_endpoint", value=redir)

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
    redir: str = "/join/2",
    redir_endpoint: Optional[str] = Cookie(None),
):
    # AWS dependencies
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    # Open redirect check
    if redir == "_redir":
        redir = redir_endpoint

    hostname = urlparse(redir).netloc

    if hostname != "" and hostname != options.get("http", {}).get(
        "domain", "my.hackucf.org"
    ):
        redir = "/join/2"

    if code is None:
        return Errors.generate(
            request,
            401,
            "You declined Discord log-in",
            essay="We need your Discord account to log into myHack@UCF.",
        )

    # Get data from Discord
    oauth = OAuth2Session(
        options.get("discord").get("client_id"),
        redirect_uri=options.get("discord").get("redirect_base") + "_redir",
        scope=options.get("discord")["scope"],
    )

    token = oauth.fetch_token(
        "https://discord.com/api/oauth2/token",
        client_id=options.get("discord").get("client_id"),
        client_secret=options.get("discord").get("secret"),
        # authorization_response=code
        code=code,
    )

    r = oauth.get("https://discord.com/api/users/@me")
    discordData = r.json()

    # Generate a new user ID or reuse an existing one.
    query_for_id = table.scan(
        FilterExpression=Attr("discord_id").eq(str(discordData["id"]))
    )
    query_for_id = query_for_id.get("Items")

    # BACKPORT: I didn't realize that Snowflakes were strings because of an integer overflow bug.
    # So this will do a query for the "mistaken" value and then fix its data.
    if not query_for_id:
        print("Beginning Discord ID attribute migration...")
        query_for_id = table.scan(
            FilterExpression=Attr("discord_id").eq(int(discordData["id"]))
        )
        query_for_id = query_for_id.get("Items")

        if query_for_id:
            table.update_item(
                Key={"id": query_for_id[0].get("id")},
                UpdateExpression="SET discord_id = :discord_id",
                ExpressionAttributeValues={":discord_id": str(discordData["id"])},
            )



    is_new = False
    print(query_for_id)

    if query_for_id:
        query_for_id = query_for_id[0]
        member_id = query_for_id.get("id")
        do_sudo = query_for_id.get("sudo")
        is_full_member = query_for_id.get("is_full_member")
        infra_email = query_for_id.get("infra_email", "")
    else:
        is_full_member = False
        member_id = str(uuid.uuid4())
        do_sudo = False
        is_new = True
        infra_email = ""

        # Make user join the Hack@UCF Discord, if it's their first rodeo.
        discord_id = str(discordData["id"])
        headers = {
            "Authorization": f"Bot {options.get('discord', {}).get('bot_token')}",
            "Content-Type": "application/json",
            "X-Audit-Log-Reason": "Hack@UCF OnboardLite Bot",
        }
        put_join_guild = {"access_token": token["access_token"]}
        req = requests.put(
            f"https://discordapp.com/api/guilds/{options.get('discord', {}).get('guild_id')}/members/{discord_id}",
            headers=headers,
            data=json.dumps(put_join_guild),
        )

    data = {
        "id": member_id,
        "discord_id": int(discordData["id"]),
        "discord": {
            "email": discordData["email"],
            "mfa": discordData["mfa_enabled"],
            "avatar": f"https://cdn.discordapp.com/avatars/{discordData['id']}/{discordData['avatar']}.png?size=512",
            "banner": f"https://cdn.discordapp.com/banners/{discordData['id']}/{discordData['banner']}.png?size=1536",
            "color": discordData["accent_color"],
            "nitro": discordData["public_flags"],
            "locale": discordData["locale"],
            "username": discordData["username"],
        },
        "email": discordData["email"]
        ## Consider making this a separate table.
        # "attendance": None # t/f based on dict/object keyed on iso-8601 date.
    }

    # Populate the full table.
    full_data = UserModel(**data).dict()

    # Push data back to DynamoDB
    if is_new:
        table.put_item(Item=full_data)
    else:
        table.update_item(
            Key={"id": member_id},
            UpdateExpression="SET discord = :discord",
            ExpressionAttributeValues={":discord": full_data["discord"]},
        )

    # Create JWT. This should be the only way to issue JWTs.
    jwtData = {
        "discord": token,
        "name": discordData["username"],
        "pfp": full_data["discord"]["avatar"],
        "id": member_id,
        "sudo": do_sudo,
        "is_full_member": is_full_member,
        "issued": time.time(),
        "infra_email": infra_email,
    }
    bearer = jwt.encode(
        jwtData,
        options.get("jwt").get("secret"),
        algorithm=options.get("jwt").get("algorithm"),
    )
    rr = RedirectResponse(redir, status_code=status.HTTP_302_FOUND)
    rr.set_cookie(key="token", value=bearer)

    # Clear redirect cookie.
    rr.delete_cookie("redir_endpoint")

    return rr


"""
Renders the landing page for the sign-up flow.
"""


@app.get("/join/")
async def join(request: Request, token: Optional[str] = Cookie(None)):
    if token == None:
        return templates.TemplateResponse("signup.html", {"request": request})
    else:
        return RedirectResponse("/join/2/", status_code=status.HTTP_302_FOUND)


"""
Renders a basic "my membership" page
"""


@app.get("/profile/")
@Authentication.member
async def profile(
    request: Request,
    token: Optional[str] = Cookie(None),
    payload: Optional[object] = {},
):
    # Get data from DynamoDB
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    print(token)

    user_data = table.get_item(Key={"id": payload.get("id")}).get("Item", None)

    # Re-run approval workflow.
    Approve.approve_member(payload.get("id"))

    return templates.TemplateResponse(
        "profile.html", {"request": request, "user_data": user_data}
    )


"""
Renders a Kennelish form page, complete with stylings and UI controls.
"""


@app.get("/join/{num}/")
@Authentication.member
async def forms(
    request: Request,
    token: Optional[str] = Cookie(None),
    payload: Optional[object] = {},
    num: str = 1,
):
    # AWS dependencies
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    if num == "1":
        return RedirectResponse("/join/", status_code=status.HTTP_302_FOUND)

    data = Options.get_form_body(num)

    # Get data from DynamoDB
    user_data = table.get_item(Key={"id": payload.get("id")}).get("Item", None)

    # Have Kennelish parse the data.
    body = Kennelish.parse(data, user_data)

    # return num
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "icon": payload["pfp"],
            "name": payload["name"],
            "id": payload["id"],
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

import logging
import uuid

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.models.user import (
    DiscordModel,
    EthicsFormModel,  # Import the EthicsFormModel
    UserModel,
)
from app.util.authentication import Authentication
from app.util.database import get_session
from app.util.errors import Errors
from app.util.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["API"], responses=Errors.basic_http())

# Hard-coded users
hardcoded_users = [
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000001"), "discord_id": "000000000001", "first_name": "Admin User", "sudo": True, "did_pay_dues": True, "ethics_form": {"signtime": 1}},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000002"), "discord_id": "000000000002", "first_name": "Dues Paying Member", "sudo": False, "did_pay_dues": True, "ethics_form": {"signtime": 1}},
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "discord_id": "000000000003",
        "first_name": "Ethics Form Filled Out, No Payment",
        "sudo": False,
        "did_pay_dues": False,
        "ethics_form": {"signtime": 1},
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000004"),
        "discord_id": "000000000004",
        "first_name": "No Activity Beyond Account Creation 1",
        "sudo": False,
        "did_pay_dues": False,
        "ethics_form": {"signtime": 0},
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000005"),
        "discord_id": "000000000005",
        "first_name": "No Activity Beyond Account Creation 2",
        "sudo": False,
        "did_pay_dues": False,
        "ethics_form": {"signtime": 0},
    },
]


def create_hardcoded_users(session: Session):
    for user_data in hardcoded_users:
        statement = select(UserModel).where(UserModel.id == user_data["id"])
        result = session.exec(statement).one_or_none()
        if not result:
            ethics_form = EthicsFormModel(signtime=user_data["ethics_form"]["signtime"])
            user = UserModel(
                id=user_data["id"], discord_id=user_data["discord_id"], name=user_data["first_name"], sudo=user_data["sudo"], did_pay_dues=user_data["did_pay_dues"], ethics_form=ethics_form
            )
            discord_user = DiscordModel(username=f"devuser-{user_data['first_name']}", email=f"devuser-{user_data['id']}@mail.com", user_id=user_data["id"], user=user)
            session.add(user)
            session.add(discord_user)
            session.commit()
            session.refresh(user)
            session.refresh(discord_user)


@router.get("/user/", response_class=HTMLResponse)
async def create_dev_user(request: Request, session: Session = Depends(get_session), sudo: bool = False):
    if request.client.host not in ["127.0.0.1", "localhost"]:
        return Errors.generate(
            request,
            403,
            "Forbidden",
            essay="This endpoint is only available on localhost.",
        )

    create_hardcoded_users(session)

    return """
    <html>
        <head>
            <link rel="stylesheet" type="text/css" href="/static/hackucf.css">
        </head>
        <body>
            <form action="/dev/select_user/" method="post">
                <label for="user">Select User:</label>
                <select name="user_id" id="user">
                    <option value="00000000-0000-0000-0000-000000000001">Admin User</option>
                    <option value="00000000-0000-0000-0000-000000000002">Dues Paying Member</option>
                    <option value="00000000-0000-0000-0000-000000000003">Ethics Form Filled Out, No Payment</option>
                    <option value="00000000-0000-0000-0000-000000000004">No Activity Beyond Account Creation 1</option>
                    <option value="00000000-0000-0000-0000-000000000005">No Activity Beyond Account Creation 2</option>
                </select>
                <input type="submit" value="Login">
            </form>
        </body>
    </html>
    """


@router.post("/select_user/")
async def select_user(request: Request, user_id: str = Form(...), session: Session = Depends(get_session)):
    statement = select(UserModel).where(UserModel.id == uuid.UUID(user_id))
    user = session.exec(statement).one_or_none()

    if not user:
        return Errors.generate(
            request,
            404,
            "User not found",
            essay="The selected user does not exist.",
        )

    # Create JWT token for the user
    bearer = Authentication.create_jwt(user)
    rr = RedirectResponse("/profile", status_code=status.HTTP_302_FOUND)
    max_age = Settings().jwt.lifetime_sudo if user.sudo else Settings().jwt.lifetime_user
    rr.set_cookie(
        key="token",
        value=bearer,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=max_age,
    )

    return rr

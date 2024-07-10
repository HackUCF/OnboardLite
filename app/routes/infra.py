import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.models.info import InfoModel
from app.models.user import PublicContact, UserModel
from app.util.approve import Approve
from app.util.authentication import Authentication
from app.util.database import get_session
from app.util.discord import Discord
from app.util.email import Email
from app.util.errors import Errors
from app.util.limiter import RateLimiter
from app.util.settings import Settings

logger = logging.getLogger(__name__)


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/infra", tags=["Infra"], responses=Errors.basic_http())


@router.get("/")
async def get_root():
    """
    Get API information.
    """
    return InfoModel(
        name="Onboard Infra",
        description="Infrastructure Management via Onboard.",
        credits=[
            PublicContact(
                first_name="Jonathan",
                surname="Styles",
                ops_email="jstyles@hackucf.org",
            ),
        ],
    )


@router.get("/openvpn")
@Authentication.member
async def download_file(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
):
    """
    An endpoint to Download OpenVPN profile
    """
    # Replace 'path/to/your/file.txt' with the actual path to your file
    file_path = "../HackUCF.ovpn"
    return FileResponse(
        file_path, filename="HackUCF.ovpn", media_type="application/octet-stream"
    )

import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlmodel import Session, select

from ..models.info import InfoModel
from ..models.user import PublicContact, UserModel
from ..util.approve import Approve
from ..util.authentication import Authentication
from ..util.database import get_session
from ..util.discord import Discord
from ..util.email import Email
from ..util.errors import Errors
from ..util.limiter import RateLimiter
from ..util.settings import Settings

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

ERR_VPN_CONFIG_NOT_FOUND = HTTPException(status_code=500, detail="HackUCF OpenVPN Config Not Found")

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
    if not Path(file_path).exists():
        ## Return 500 ISE
        raise ERR_VPN_CONFIG_NOT_FOUND
    else:
        return FileResponse(
            file_path, filename="HackUCF.ovpn", media_type="application/octet-stream"
        )

# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from app.models.info import InfoModel
from app.models.user import PublicContact

logger = logging.getLogger(__name__)


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/infra", tags=["Infra"])


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

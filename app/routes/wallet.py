# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import json
import logging
import os
import tempfile
import uuid
from typing import Optional

import requests
from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import RedirectResponse
from google.auth import crypt, jwt
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from passes_rs_py import generate_pass
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models.info import InfoModel
from app.models.user import PublicContact, UserModel, user_to_dict
from app.util.authentication import Authentication
from app.util.database import get_session
from app.util.errors import Errors
from app.util.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/wallet",
    tags=["API", "MobileWallet"],
    responses=Errors.basic_http(),
)


class GoogleWallet:
    def __init__(self):
        self.auth_dict = json.loads(Settings().google_wallet.auth_json.get_secret_value())
        # Set up authenticated client
        self.auth()

    # [END setup]

    # [START auth]
    def auth(self):
        """Create authenticated HTTP client using a service account file."""
        self.credentials = Credentials.from_service_account_info(
            self.auth_dict,
            scopes=["https://www.googleapis.com/auth/wallet_object.issuer"],
        )

        self.client = build("walletobjects", "v1", credentials=self.credentials)

    # [END auth]
    def create_object(self, issuer_id: str, class_suffix: str, user_data: UserModel) -> str:
        """Create an object.

        Args:
            issuer_id (str): The issuer ID being used for this request.
            class_suffix (str): Developer-defined unique ID for the pass class.
            object_suffix (str): Developer-defined unique ID for the pass object.

        Returns:
            The pass object ID: f"{issuer_id}.{object_suffix}"
        """
        user_id = str(user_data.id)
        # Check if the object exists
        try:
            self.client.loyaltyobject().get(resourceId=f"{issuer_id}.{user_data.id}").execute()
        except HttpError as e:
            if e.status_code != 404:
                # Something else went wrong...
                logger.error("Google Wallet" + str(e.error_details))
                return f"{issuer_id}.{user_id}"
        else:
            logger.info(f"Wallet Object {issuer_id}.{user_id} already exists!")
            return f"{issuer_id}.{user_id}"

        # See link below for more information on required properties
        # https://developers.google.com/wallet/retail/loyalty-cards/rest/v1/loyaltyobject
        new_object = {
            "id": f"{issuer_id}.{user_id}",
            "classId": f"{issuer_id}.{class_suffix}",
            "state": "ACTIVE",
            "heroImage": {
                "sourceUri": {"uri": "https://cdn.hackucf.org/newsletter/banner.png"},
                "contentDescription": {
                    "defaultValue": {
                        "language": "en-US",
                        "value": "Hack@UCF Banner Logo",
                    }
                },
            },
            "hexBackgroundColor": "#231f20",
            "logo": {
                "sourceUri": {"uri": "https://cdn.hackucf.org/PFP.png"},
                "contentDescription": {
                    "defaultValue": {
                        "language": "en-US",
                        "value": "LOGO_IMAGE_DESCRIPTION",
                    }
                },
            },
            "cardTitle": {
                "defaultValue": {
                    "language": "en-US",
                    "value": "Hack@UCF Membership ID",
                }
            },
            "subheader": {"defaultValue": {"language": "en-US", "value": "Name "}},
            "header": {
                "defaultValue": {
                    "language": "en-US",
                    "value": str(user_data.first_name) + " " + str(user_data.surname),
                }
            },
            "linksModuleData": {
                "uris": [
                    {
                        "uri": "https://join.hackucf.org/profile",
                        "description": "Profile Page",
                        "id": "PROFILE",
                    },
                ]
            },
            "barcode": {
                "type": "QR_CODE",
                "value": user_id,
                "alternateText": user_data.discord.username,
            },
            "locations": [
                {
                    "latitude": 28.60183940476708,
                    "longitude": -81.19807063116282,
                },
            ],
            "accountId": user_id,
            "accountName": str(user_data.first_name) + " " + str(user_data.surname),
        }

        # Create the object
        response = self.client.genericobject().insert(body=new_object).execute()

        return f"{issuer_id}.{user_id}"

    def create_jwt_existing_objects(self, issuer_id: str, user_id, class_id) -> str:
        """Generate a signed JWT that references an existing pass object.

        When the user opens the "Add to Google Wallet" URL and saves the pass to
        their wallet, the pass objects defined in the JWT are added to the
        user's Google Wallet app. This allows the user to save multiple pass
        objects in one API call.

        The objects to add must follow the below format:

        {
            'id': 'ISSUER_ID.OBJECT_SUFFIX',
            'classId': 'ISSUER_ID.CLASS_SUFFIX'
        }

        Args:
            issuer_id (str): The issuer ID being used for this request.

        Returns:
            An "Add to Google Wallet" link
        """

        # Multiple pass types can be added at the same time
        # At least one type must be specified in the JWT claims
        # Note: Make sure to replace the placeholder class and object suffixes
        objects_to_add = {
            # Loyalty cards
            "genericObjects": [
                {
                    "id": f"{issuer_id}.{user_id}",
                    "classId": f"{issuer_id}.{class_id}",
                }
            ],
        }

        # Create the JWT claims
        claims = {
            "iss": self.credentials.service_account_email,
            "aud": "google",
            "origins": ["join.hackucf.org"],
            "typ": "savetowallet",
            "payload": objects_to_add,
        }

        # The service account credentials are used to sign the JWT
        signer = crypt.RSASigner.from_service_account_info(self.auth_dict)
        token = jwt.encode(signer, claims).decode("utf-8")

        return f"https://pay.google.com/gp/v/save/{token}"

    # [END jwtExisting]


if Settings().google_wallet.enable:
    google_wallet = GoogleWallet()


def get_img(url):
    """
    Used to get Discord image.
    """
    resp = requests.get(url, stream=True)
    status = resp.status_code
    if status < 400:
        return resp.raw.read()
    else:
        return get_img("https://cdn.hackucf.org/PFP.png")


def apple_wallet(user_data):
    """
    User data -> Apple Wallet blob using passes_rs_py
    """
    # Get certificate and key paths
    key_path = str(Settings().apple_wallet.pki_dir / "hackucf.key")
    cert_path = str(Settings().apple_wallet.pki_dir / "hackucf.pem")

    # Get asset paths
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static", "apple_wallet")
    icon_path = os.path.join(static_dir, "icon.png")
    icon2x_path = os.path.join(static_dir, "icon@2x.png")
    logo_path = os.path.join(static_dir, "logo_reg.png")
    logo2x_path = os.path.join(static_dir, "logo_reg@2x.png")

    # Check if required files exist
    if not os.path.exists(key_path):
        logger.error(f"File not found: {key_path}")
        raise FileNotFoundError(f"File not found: {key_path}")

    if not os.path.exists(cert_path):
        logger.error(f"File not found: {cert_path}")
        raise FileNotFoundError(f"File not found: {cert_path}")

    if not os.path.exists(icon_path):
        logger.error(f"File not found: {icon_path}")
        raise FileNotFoundError(f"File not found: {icon2x_path}")

    if not os.path.exists(icon2x_path):
        logger.error(f"File not found: {icon2x_path}")
        raise FileNotFoundError(f"File not found: {icon2x_path}")

    if not os.path.exists(logo_path):
        logger.error(f"File not found: {logo_path}")
        raise FileNotFoundError(f"File not found: {logo_path}")

    if not os.path.exists(logo2x_path):
        logger.error(f"File not found: {logo2x_path}")
        raise FileNotFoundError(f"File not found: {logo2x_path}")

    # Create pass config as JSON string (required by passes_rs_py)
    # This follows the Apple Wallet pass.json format specification

    # Safely extract user data with proper null handling
    user_id = str(user_data.get("id", ""))
    first_name = user_data.get("first_name") or ""
    surname = user_data.get("surname") or ""
    full_name = f"{first_name} {surname}".strip() or "Member"

    # Handle discord data safely
    discord_data = user_data.get("discord") or {}
    discord_username = ""
    if isinstance(discord_data, dict):
        discord_username = discord_data.get("username") or ""

    # Handle ops email safely
    ops_email = user_data.get("ops_email") or ""

    config_dict = {
        "passTypeIdentifier": "pass.org.hackucf.join",
        "formatVersion": 1,
        "teamIdentifier": "VWTW9R97Q4",
        "organizationName": "Hack@UCF",
        "serialNumber": user_id,
        "description": "Hack@UCF Membership ID",
        "locations": [{"latitude": 28.601366109876327, "longitude": -81.19867691612126, "relevantText": "You're near the CyberLab!"}],
        "foregroundColor": "#D2990B",
        "backgroundColor": "#1C1C1C",
        "labelColor": "#ffffff",
        "logoText": "",
        "barcodes": [{"format": "PKBarcodeFormatQR", "message": user_id, "messageEncoding": "iso-8859-1", "altText": discord_username}],
        "generic": {
            "primaryFields": [{"label": "Name", "key": "name", "value": full_name}],
            "secondaryFields": [{"label": "Infra Email", "key": "infra", "value": ops_email}],
            "auxiliaryFields": [],
            "backFields": [
                {
                    "label": "View Profile",
                    "key": "view-profile",
                    "value": "You can view and edit your profile at https://join.hackucf.org/profile.",
                    "attributedValue": "You can view and edit your profile at <a href='https://join.hackucf.org/profile'>join.hackucf.org</a>.",
                },
                {
                    "label": "Check In",
                    "key": "check-in",
                    "value": "At a meeting? Visit https://hackucf.org/signin to sign in",
                    "attributedValue": "At a meeting? Visit <a href='https://hackucf.org/signin'>hackucf.org/signin</a> to sign in.",
                },
            ],
            "headerFields": [],
        },
    }

    # Validate that no values are None before JSON serialization
    def validate_no_nulls(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if value is None:
                    logger.error(f"Found null value at {path}.{key}")
                    raise ValueError(f"Null value found at {path}.{key}")
                validate_no_nulls(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                validate_no_nulls(item, f"{path}[{i}]")

    # Validate the config before serialization
    validate_no_nulls(config_dict, "config")

    config_json = json.dumps(config_dict)
    logger.debug(f"Pass config JSON length: {len(config_json)} characters")

    # Create temporary output file
    with tempfile.NamedTemporaryFile(suffix=".pkpass", delete=False) as tmp_file:
        output_path = tmp_file.name

    try:
        # Generate the pass using JSON config string with all assets
        generate_pass(config_json, cert_path, key_path, output_path, icon_path, icon2x_path, logo_path, logo2x_path)

        # Read the generated pass file
        with open(output_path, "rb") as f:
            pass_data = f.read()

        return pass_data

    except Exception as e:
        logger.error(f"Failed to generate Apple Wallet pass for user {user_data.get('id', 'unknown')}: {e}")
        raise e
    finally:
        # Clean up temporary file
        if os.path.exists(output_path):
            os.unlink(output_path)


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
    statement = select(UserModel).where(UserModel.id == uuid.UUID(user_jwt["id"])).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    user_data = user_to_dict(session.exec(statement).one_or_none())

    pass_data = apple_wallet(user_data)

    return Response(
        content=pass_data,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": 'attachment; filename="hackucf.pkpass"'},
    )


@router.get("/google")
@Authentication.member
async def google_gen(
    request: Request,
    token: Optional[str] = Cookie(None),
    user_jwt: Optional[object] = {},
    session=Depends(get_session),
):
    if not Settings().google_wallet.enable:
        return Errors.generate()
    statement = select(UserModel).where(UserModel.id == uuid.UUID(user_jwt["id"])).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    issuer_id = Settings().google_wallet.issuer_id
    class_suffix = Settings().google_wallet.class_suffix
    user_data = session.exec(statement).one_or_none()
    object_id = google_wallet.create_object(issuer_id, class_suffix, user_data)
    redir_url = google_wallet.create_jwt_existing_objects(
        issuer_id,
        str(user_data.id),
        class_suffix,
    )

    return RedirectResponse(redir_url)

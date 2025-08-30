# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import json
import logging
from typing import Any, Dict, Optional

from google.auth import crypt, jwt
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models.user import UserModel
from app.util.settings import Settings

logger = logging.getLogger(__name__)


class GoogleWalletManager:
    """
    Google Wallet pass manager for Hack@UCF membership cards.

    Handles the creation and management of Google Wallet pass objects,
    including authentication, object creation, and JWT generation.
    """

    def __init__(self):
        """Initialize the Google Wallet manager with authentication."""
        self.settings = Settings()

        if not self.settings.google_wallet.enable:
            raise ValueError("Google Wallet is not enabled in settings")

        self.auth_dict = json.loads(self.settings.google_wallet.auth_json.get_secret_value())
        self.issuer_id = self.settings.google_wallet.issuer_id
        self.class_suffix = self.settings.google_wallet.class_suffix

        # Set up authenticated client
        self._authenticate()

    def _authenticate(self) -> None:
        """Create authenticated HTTP client using service account credentials."""
        try:
            self.credentials = Credentials.from_service_account_info(
                self.auth_dict,
                scopes=["https://www.googleapis.com/auth/wallet_object.issuer"],
            )
            self.client = build("walletobjects", "v1", credentials=self.credentials)
            logger.info("Google Wallet client authenticated successfully")
        except Exception as e:
            logger.error(f"Failed to authenticate Google Wallet client: {e}")
            raise ValueError(f"Google Wallet authentication failed: {e}") from e

    def _create_pass_object_data(self, user_data: UserModel) -> Dict[str, Any]:
        """
        Create the pass object data dictionary from user model.

        Args:
            user_data: UserModel instance containing user information

        Returns:
            Pass object data dictionary ready for Google Wallet API
        """
        # ensure first name and discord username are not empty (surname is optional)
        missing_fields = []
        if not user_data.first_name:
            missing_fields.append("first_name")
        if not user_data.discord or not user_data.discord.username:
            missing_fields.append("discord.username")

        if missing_fields:
            logger.error(f"User data is incomplete. Missing fields: {', '.join(missing_fields)}")
            raise ValueError("User data is incomplete")

        user_id = str(user_data.id)
        # After validation, we know first_name is not None/empty
        full_name = str(user_data.first_name)
        if user_data.surname:
            full_name += f" {user_data.surname}"
        discord_username = user_data.discord.username if user_data.discord else ""

        return {
            "id": f"{self.issuer_id}.{user_id}",
            "classId": f"{self.issuer_id}.{self.class_suffix}",
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
                    "value": full_name,
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
                "alternateText": discord_username,
            },
            "locations": [
                {
                    "latitude": 28.60183940476708,
                    "longitude": -81.19807063116282,
                },
            ],
            "accountId": user_id,
            "accountName": full_name,
        }

    def create_object(self, user_data: UserModel) -> str:
        """
        Create a Google Wallet pass object for the given user.

        Args:
            user_data: UserModel instance containing user information

        Returns:
            The pass object ID in format: "{issuer_id}.{user_id}"

        Raises:
            ValueError: If object creation fails
        """
        user_id = str(user_data.id)
        object_id = f"{self.issuer_id}.{user_id}"

        try:
            # Check if the object already exists
            try:
                self.client.genericobject().get(resourceId=object_id).execute()
                logger.info(f"Google Wallet object {object_id} already exists")
                return object_id
            except HttpError as e:
                if e.status_code == 404:
                    # Object doesn't exist, continue with creation
                    pass
                else:
                    # Some other error occurred
                    logger.error(f"Error checking existing Google Wallet object: {e.error_details}")
                    raise ValueError(f"Failed to check existing object: {e}") from e

            # Create new object
            try:
                new_object = self._create_pass_object_data(user_data)
            except ValueError as err:
                logger.error(f"Failed to create Google Wallet object for user {user_id}: {err}")
                raise ValueError(f"Failed to create object: {err}") from err

            self.client.genericobject().insert(body=new_object).execute()
            logger.info(f"Successfully created Google Wallet object {object_id}")

            return object_id

        except Exception as e:
            logger.error(f"Failed to create Google Wallet object for user {user_id}: {e}")
            raise ValueError(f"Google Wallet object creation failed: {str(e)}") from e

    def create_jwt_save_url(self, user_data: UserModel) -> str:
        """
        Generate a signed JWT that creates an "Add to Google Wallet" URL.

        Args:
            user_data: UserModel instance containing user information

        Returns:
            An "Add to Google Wallet" URL with embedded JWT

        Raises:
            ValueError: If JWT creation fails
        """
        try:
            user_id = str(user_data.id)

            # Ensure the object exists first
            object_id = self.create_object(user_data)

            # Define objects to add to wallet
            objects_to_add = {
                "genericObjects": [
                    {
                        "id": object_id,
                        "classId": f"{self.issuer_id}.{self.class_suffix}",
                    }
                ],
            }

            # Create JWT claims
            claims = {
                "iss": self.credentials.service_account_email,
                "aud": "google",
                "origins": ["join.hackucf.org"],
                "typ": "savetowallet",
                "payload": objects_to_add,
            }

            # Sign the JWT
            signer = crypt.RSASigner.from_service_account_info(self.auth_dict)
            token = jwt.encode(signer, claims).decode("utf-8")

            save_url = f"https://pay.google.com/gp/v/save/{token}"
            logger.info(f"Generated Google Wallet save URL for user {user_id}")

            return save_url

        except Exception as e:
            logger.error(f"Failed to create Google Wallet JWT for user {user_data.id}: {e}")
            raise ValueError(f"Google Wallet JWT creation failed: {str(e)}") from e

    def get_object_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a Google Wallet object for a user.

        Args:
            user_id: User ID to check

        Returns:
            Object data if it exists, None if not found

        Raises:
            ValueError: If API call fails for reasons other than not found
        """
        object_id = f"{self.issuer_id}.{user_id}"

        try:
            response = self.client.genericobject().get(resourceId=object_id).execute()
            return response
        except HttpError as e:
            if e.status_code == 404:
                return None
            else:
                logger.error(f"Error getting Google Wallet object status: {e.error_details}")
                raise ValueError(f"Failed to get object status: {e}") from e

    def is_enabled(self) -> bool:
        """
        Check if Google Wallet is enabled in settings.

        Returns:
            True if Google Wallet is enabled, False otherwise
        """
        return self.settings.google_wallet.enable

    def get_config_info(self) -> Dict[str, Any]:
        """
        Get Google Wallet configuration information for debugging.

        Returns:
            Dictionary with configuration details (secrets redacted)
        """
        return {
            "enabled": self.settings.google_wallet.enable,
            "issuer_id": self.issuer_id,
            "class_suffix": self.class_suffix,
            "service_account_email": self.credentials.service_account_email if hasattr(self, "credentials") else "Not authenticated",
            "auth_configured": bool(self.auth_dict),
        }

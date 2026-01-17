# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import json
import logging
import os
import tempfile
from typing import Any, Dict

from passes_rs_py import generate_pass

from app.util.settings import Settings

logger = logging.getLogger(__name__)


class AppleWalletGenerator:
    """
    Apple Wallet pass generator for Hack@UCF membership cards.

    Handles the creation of .pkpass files using the passes_rs_py library,
    including proper asset management and user data integration.
    """

    def __init__(self):
        """Initialize the Apple Wallet generator with asset paths."""
        self.settings = Settings()

        # Get certificate and key paths
        self.key_path = str(self.settings.apple_wallet.pki_dir / "hackucf.key")
        self.cert_path = str(self.settings.apple_wallet.pki_dir / "hackucf.pem")

        # Get asset paths
        static_dir = os.path.join(os.path.dirname(__file__), "..", "static", "apple_wallet")
        self.icon_path = os.path.join(static_dir, "icon.png")
        self.icon2x_path = os.path.join(static_dir, "icon@2x.png")
        self.logo_path = os.path.join(static_dir, "logo_reg.png")
        self.logo2x_path = os.path.join(static_dir, "logo_reg@2x.png")

        # Validate required files exist
        self._validate_required_files()

    def _validate_required_files(self) -> None:
        """Validate that all required files exist."""
        required_files = {
            "Certificate": self.cert_path,
            "Private Key": self.key_path,
            "Icon": self.icon_path,
            "Icon@2x": self.icon2x_path,
            "Logo": self.logo_path,
            "Logo@2x": self.logo2x_path,
        }

        for file_type, file_path in required_files.items():
            if not os.path.exists(file_path):
                logger.error(f"{file_type} not found: {file_path}")
                raise FileNotFoundError(f"{file_type} not found: {file_path}")

    def _create_pass_config(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create the pass configuration dictionary from user data.

        Args:
            user_data: Dictionary containing user information

        Returns:
            Pass configuration dictionary ready for JSON serialization
        """
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

        config_dict = {
            "passTypeIdentifier": "pass.org.hackucf.join",
            "formatVersion": 1,
            "teamIdentifier": "VWTW9R97Q4",
            "organizationName": "Hack@UCF",
            "serialNumber": user_id,
            "description": "Hack@UCF Membership ID",
            "locations": [{"latitude": 28.601366109876327, "longitude": -81.19867691612126, "relevantText": "You're near the CyberLab!"}],
            "foregroundColor": "rgb(210, 153, 11)",
            "backgroundColor": "rgb(28, 28, 28)",
            "labelColor": "rgb(255, 255, 255)",
            "logoText": "",
            "barcodes": [{"format": "PKBarcodeFormatQR", "message": user_id, "messageEncoding": "iso-8859-1", "altText": discord_username}],
            "generic": {
                "primaryFields": [{"label": "Name", "key": "name", "value": full_name}],
                "secondaryFields": [],
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

        return config_dict

    def _validate_config(self, config_dict: Dict[str, Any], path: str = "") -> None:
        """
        Validate that no values are None before JSON serialization.

        Args:
            config_dict: Configuration dictionary to validate
            path: Current path for error reporting

        Raises:
            ValueError: If null values are found
        """
        if isinstance(config_dict, dict):
            for key, value in config_dict.items():
                if value is None:
                    logger.error(f"Found null value at {path}.{key}")
                    raise ValueError(f"Null value found at {path}.{key}")
                self._validate_config(value, f"{path}.{key}")
        elif isinstance(config_dict, list):
            for i, item in enumerate(config_dict):
                self._validate_config(item, f"{path}[{i}]")

    def generate_pass(self, user_data: Dict[str, Any]) -> bytes:
        """
        Generate an Apple Wallet pass for the given user.

        Args:
            user_data: Dictionary containing user information including:
                - id: User UUID
                - first_name: User's first name
                - surname: User's surname
                - discord: Dictionary with discord info (optional)
                - ops_email: Infrastructure email (optional)

        Returns:
            bytes: The generated .pkpass file content

        Raises:
            ValueError: If user data is invalid or pass generation fails
            FileNotFoundError: If required assets are missing
        """
        try:
            # Create pass configuration
            config_dict = self._create_pass_config(user_data)

            # Validate configuration
            self._validate_config(config_dict, "config")

            # Convert to JSON
            config_json = json.dumps(config_dict)
            logger.debug(f"Generated pass config JSON ({len(config_json)} chars)")

            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix=".pkpass", delete=False) as tmp_file:
                output_path = tmp_file.name

            try:
                # Generate the pass using passes_rs_py with all assets
                generate_pass(
                    config=config_json,
                    cert_path=self.cert_path,
                    key_path=self.key_path,
                    output_path=output_path,
                    icon_path=self.icon_path,
                    icon2x_path=self.icon2x_path,
                    logo_path=self.logo_path,
                    logo2x_path=self.logo2x_path,
                    # ignore_expired=True  # Add this if you want to ignore expired certificates
                )

                # Read the generated pass file
                with open(output_path, "rb") as f:
                    pass_data = f.read()

                logger.info(f"Successfully generated Apple Wallet pass for user {user_data.get('id', 'unknown')}")
                return pass_data

            finally:
                # Clean up temporary file
                if os.path.exists(output_path):
                    os.unlink(output_path)

        except Exception as e:
            logger.error(f"Failed to generate Apple Wallet pass for user {user_data.get('id', 'unknown')}: {e}")
            raise ValueError(f"Apple Wallet pass generation failed: {str(e)}") from e

    def get_asset_info(self) -> Dict[str, str]:
        """
        Get information about the configured assets.

        Returns:
            Dictionary with asset paths and their existence status
        """
        assets = {
            "certificate": self.cert_path,
            "private_key": self.key_path,
            "icon": self.icon_path,
            "icon_2x": self.icon2x_path,
            "logo": self.logo_path,
            "logo_2x": self.logo2x_path,
        }

        return {name: f"{path} ({'✓' if os.path.exists(path) else '✗'})" for name, path in assets.items()}

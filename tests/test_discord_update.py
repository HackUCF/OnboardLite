# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import update_discord_model_for_existing_user
from app.models.user import DiscordModel, UserModel


def test_update_discord_model_for_existing_user(session: Session, test_user: UserModel):
    """Test that the background task updates Discord model for existing users"""
    
    # Setup test data - simulate Discord API response
    original_username = test_user.discord.username
    original_avatar = test_user.discord.avatar
    
    discord_data = {
        "id": test_user.discord_id,
        "email": "updated_email@example.com", 
        "username": "updated_username",
        "avatar": "new_avatar_hash",
        "banner": "new_banner_hash",
        "mfa_enabled": True,
        "accent_color": 123456,
        "premium_type": 2,
        "locale": "en_GB"
    }
    
    # Mock the engine and session creation for the background task
    with patch('app.main.engine') as mock_engine:
        mock_session = MagicMock()
        mock_engine.__enter__ = MagicMock(return_value=mock_session)
        mock_engine.__exit__ = MagicMock(return_value=None)
        
        # Mock the session context manager
        mock_engine_instance = MagicMock()
        mock_engine_instance.__enter__ = MagicMock(return_value=mock_session)
        mock_engine_instance.__exit__ = MagicMock(return_value=None)
        
        with patch('app.main.Session') as mock_session_class:
            mock_session_class.return_value = mock_engine_instance
            
            # Mock the database query
            mock_session.exec.return_value.one_or_none.return_value = test_user
            
            # Call the background task function
            update_discord_model_for_existing_user(str(test_user.id), discord_data)
            
            # Verify the session was used correctly
            mock_session_class.assert_called_once()
            mock_session.exec.assert_called_once()
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()


def test_update_discord_model_user_not_found():
    """Test background task handles missing user gracefully"""
    
    fake_user_id = str(uuid.uuid4())
    discord_data = {"id": "123", "username": "test"}
    
    with patch('app.main.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_engine_instance = MagicMock()
        mock_engine_instance.__enter__ = MagicMock(return_value=mock_session)
        mock_engine_instance.__exit__ = MagicMock(return_value=None)
        mock_session_class.return_value = mock_engine_instance
        
        # Mock user not found
        mock_session.exec.return_value.one_or_none.return_value = None
        
        # Should not raise exception, just log warning
        update_discord_model_for_existing_user(fake_user_id, discord_data)
        
        # Should not call add or commit
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()


@pytest.mark.skip(reason="Requires full app configuration setup")
def test_oauth_calls_background_task_for_existing_user():
    """Test that OAuth endpoint adds background task for existing users"""
    # This test would require full OAuth flow mocking
    # Skipping for now as it requires extensive setup
    pass
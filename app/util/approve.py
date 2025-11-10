# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
import re
import uuid

from keycloak import KeycloakAdmin
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models.user import UserModel
from app.util.database import engine
from app.util.discord import Discord
from app.util.email import Email
from app.util.horsepass import HorsePass
from app.util.messages import load_and_render_template
from app.util.settings import Settings

logger = logging.getLogger()


class Approve:
    """
    This function will ensure a member meets all requirements to be a member, and if so, creates an
    Infra account + whitelist them to the Hack@UCF Minecraft server.

    If approval fails, dispatch a Discord message saying that something went wrong and how to fix it.
    """

    def __init__(self):
        pass

    @staticmethod
    def sanitize_username(username: str) -> str:
        """Strip invalid characters from username"""
        # Remove characters: <>& "' spaces tabs vertical tabs $%!#?§,;:*~/\|^=[]{}()`
        invalid_chars = r"[<>&\"'\s\v\t$%!#?§,;:*~/\\|^=\[\]{}()`]"
        return re.sub(invalid_chars, "", username)

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Strip invalid characters from first and last names"""
        # Remove dangerous characters but keep common name chars like hyphens, apostrophes, spaces
        invalid_chars = r"[<>&\"\v$%!#?§;*~/\\|^=\[\]{}()]"
        result = re.sub(invalid_chars, "", name)
        logger.debug(f"sanitize_name: '{name}' -> '{result}'")
        return result

    def provision_infra(
        member_id: uuid.UUID,
        user_data,
        reset_password=False,
    ):
        username = Approve.sanitize_username(user_data.discord.username[:20]).rstrip(".")
        first_name = Approve.sanitize_name(user_data.first_name)
        last_name = Approve.sanitize_name(user_data.surname)

        password = HorsePass.gen()
        admin = KeycloakAdmin(
            server_url=Settings().keycloak.url,
            username=Settings().keycloak.username,
            password=Settings().keycloak.password.get_secret_value(),
            realm_name=Settings().keycloak.realm,
            verify=True,
        )

        try:
            users = admin.get_users({"q": f"onboard-membership-id:{str(user_data.id)}"})
        except Exception:
            logger.exception("Keycloak Error - Failed to retrieve users by onboard-membership-id")
            raise
        if len(users) == 1:
            try:
                if reset_password:
                    admin.set_user_password(user_id=users[0].get("id"), password=password, temporary=True)
                    return {"username": users[0].get("username"), "password": password}
                else:
                    admin.update_user(user_id=users[0].get("id"), payload={"enabled": True})
                logger.info(f"User {user_data.id} Keycloak user {users[0].get('id')} enabled")
            except Exception:
                logger.exception(f"Keycloak Error - Failed to enable user {user_data.id} ")
                raise
            logger.debug(f"User {users[0].get('id')} already exists")
            return {"username": users[0].get("username"), "password": "Account already exists. Please use the password you previously created."}

        elif len(users) > 1:
            logger.error(f"Multiple users found with onboard-membership-id:{str(user_data.id)}")
            raise ValueError("Multiple users found")
        try:
            admin.create_user(
                {
                    "email": user_data.email,
                    "username": username,
                    "enabled": True,
                    "firstName": first_name,
                    "lastName": last_name,
                    "attributes": {
                        "onboard-membership-id": str(user_data.id),
                        "discord-id": str(user_data.discord_id)
                    },
                    "credentials": [
                        {
                            "value": password,
                            "type": "secret",
                        }
                    ],
                },
                exist_ok=False,
            )
        except Exception:
            logger.exception("Keycloak Error")
            raise

        return {"username": username, "password": password}

    # !TODO finish the post-sign-up stuff + testing
    def approve_member(member_id: uuid.UUID):
        with Session(engine) as session:
            logger.info(f"Re-running approval for {str(member_id)}")
            statement = select(UserModel).where(UserModel.id == member_id).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))

            result = session.exec(statement)
            user_data = result.one_or_none()
            if not user_data:
                raise Exception("User not found.")
            # If a member was already approved, kill process.
            if user_data.is_full_member:
                logger.info("	Already full member.")
                return True

            # Sorry for the long if statement. But we consider someone a "member" iff:
            # - They have a name
            # - We have their Discord snowflake
            # - They paid dues
            # - They signed their ethics form
            if user_data.first_name and user_data.discord_id and user_data.did_pay_dues and user_data.ethics_form.signtime != 0:
                logger.info("	Newly-promoted full member!")

                discord_id = user_data.discord_id

                # Create an Infra account.
                try:
                    creds = Approve.provision_infra(member_id, user_data)
                except:
                    logger.exception("Failed to provision user account")
                    creds = {"username": None, "password": None}

                # Assign the Dues-Paying Member role
                try:
                    Discord.assign_role(discord_id, Settings().discord.member_role)
                except:
                    logger.exception("Failed to assign role")

                # Send Discord message saying they are a member
                welcome_msg = load_and_render_template("app/messages/welcome.md", user_data=user_data, creds=creds, settings=Settings())
                try:
                    Discord.send_message(discord_id, welcome_msg)
                    Email.send_email("Welcome to Hack@UCF", welcome_msg, user_data.email)
                except Exception:
                    logger.exception("Failed to send welcome message")
                # Set member as a "full" member.
                user_data.is_full_member = True
                user_data.renewal = False
                session.add(user_data)
                session.commit()
                session.refresh(user_data)

            elif user_data.did_pay_dues:
                logger.info("	Paid dues but did not do other step!")
                # Send a message on why this check failed.
                fail_msg = load_and_render_template("app/messages/membership_approval_failed.md", user_data=user_data, settings=Settings())
                Discord.send_message(user_data.discord_id, fail_msg)

            else:
                logger.info("	Did not pay dues yet.")

        return False

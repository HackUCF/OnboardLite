# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import csv
import logging
import uuid
from io import StringIO
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request, Response, status
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models.user import (
    UserModel,
    UserModelMutable,
    user_to_dict,
    user_update_instance,
)
from app.util.approve import Approve
from app.util.auth_dependencies import CurrentAdmin
from app.util.database import get_session
from app.util.discord import Discord
from app.util.email import Email
from app.util.membership_reset import MembershipReset
from app.util.messages import load_and_render_template
from app.util.settings import Settings

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/admin", tags=["Admin"], redirect_slashes=False)


@router.get("/")
async def admin(request: Request, current_admin: CurrentAdmin):
    """
    Renders the Admin home page.
    """
    return templates.TemplateResponse(
        "admin_searcher.html",
        {
            "request": request,
            "icon": current_admin["pfp"],
            "name": current_admin["name"],
            "id": current_admin["id"],
        },
    )


class InfraProvisionRequest(BaseModel):
    member_id: uuid.UUID
    reset_password: bool = False


@router.post("/infra/")
async def post_infra(
    request: Request,
    background_tasks: BackgroundTasks,
    current_admin: CurrentAdmin,
    provision_request: InfraProvisionRequest,  # ← Use request body
    session: Session = Depends(get_session),
):
    """API endpoint to FORCE-provision Infra credentials"""

    member_id = provision_request.member_id
    reset_password = provision_request.reset_password

    user_data = session.exec(select(UserModel).where(UserModel.id == member_id)).one_or_none()

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    creds = Approve.provision_infra(member_id, user_data, reset_password=reset_password)

    if not creds:
        raise HTTPException(status_code=500, detail="Failed to provision credentials")

    # Send notifications
    new_creds_msg = load_and_render_template("app/messages/manual_invite_creds.md", user_data=user_data, creds=creds, settings=Settings())
    Discord.send_message(user_data.discord_id, new_creds_msg)
    Email.send_email("Hack@UCF Private Cloud Credentials", new_creds_msg, user_data.email)

    return {
        "username": creds.get("username"),
        "password": creds.get("password"),
    }


@router.post("/refresh/")
async def get_refresh(
    request: Request,
    background_tasks: BackgroundTasks,
    current_admin: CurrentAdmin,
    member_id: Optional[uuid.UUID] = None,
    session: Session = Depends(get_session),
):
    """
    API endpoint that re-runs the member verification workflow
    """
    if member_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing member_id parameter")

    background_tasks.add_task(Approve.approve_member, member_id)

    user_data = session.exec(select(UserModel).where(UserModel.id == member_id)).one_or_none()

    if not user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"data": user_data}


@router.get("/get/")
async def admin_get_single(
    request: Request,
    current_admin: CurrentAdmin,
    member_id: Optional[uuid.UUID] = None,
    session: Session = Depends(get_session),
):
    """
    API endpoint that gets a specific user's data as JSON
    """
    if member_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing member_id parameter")

    statement = select(UserModel).where(UserModel.id == member_id).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    user_data = user_to_dict(session.exec(statement).one_or_none())

    if not user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"data": user_data}


@router.get("/get_by_snowflake/")
async def admin_get_snowflake(
    request: Request,
    current_admin: CurrentAdmin,
    discord_id: Optional[str] = "FAIL",
    session: Session = Depends(get_session),
):
    """
    API endpoint that gets a specific user's data as JSON, given a Discord snowflake.
    Designed for trusted federated systems to exchange data.
    """
    if discord_id == "FAIL":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing discord_id parameter")

    statement = select(UserModel).where(UserModel.discord_id == discord_id).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    data = user_to_dict(session.exec(statement).one_or_none())
    # if not data:
    #    # Try a legacy-user-ID search (deprecated, but still neccesary)
    #    data = table.scan(FilterExpression=Attr("discord_id").eq(int(discord_id))).get(
    #        "Items"
    #    )
    #
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # data = data[0]

    return {"data": data}


@router.post("/message/")
async def admin_post_discord_message(
    request: Request,
    current_admin: CurrentAdmin,
    member_id: Optional[uuid.UUID] = None,
    user_jwt: dict = Body(None),
    session: Session = Depends(get_session),
):
    """
    API endpoint that gets a specific user's data as JSON
    """
    if member_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing member_id parameter")

    data = session.exec(select(UserModel).where(UserModel.id == member_id)).one_or_none()

    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    message_text = user_jwt.get("msg")

    res = Discord.send_message(data.discord_id, message_text)

    if res:
        return {"msg": "Message sent."}
    else:
        return {"msg": "An error occured!"}


@router.post("/get/")
async def admin_edit(
    request: Request,
    current_admin: CurrentAdmin,
    input_data: UserModelMutable,
    session: Session = Depends(get_session),
):
    """
    API endpoint that modifies a given user's data
    """
    if not input_data.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID is required")

    member_id = input_data.id

    statement = select(UserModel).where(UserModel.id == member_id).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    member_data = session.exec(statement).one_or_none()

    if not member_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    input_data = user_to_dict(input_data)
    user_update_instance(member_data, input_data)

    session.add(member_data)
    session.commit()
    return {"data": user_to_dict(member_data), "msg": "Updated successfully!"}


@router.get("/list")
async def admin_list(
    request: Request,
    current_admin: CurrentAdmin,
    session: Session = Depends(get_session),
):
    """
    API endpoint that dumps all users as JSON.
    """
    statement = select(UserModel).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    users = session.exec(statement)
    data = []
    for user in users:
        user = user_to_dict(user)
        data.append(user)

    return {"data": data}


@router.get("/csv")
async def admin_list_csv(
    request: Request,
    current_admin: CurrentAdmin,
    session: Session = Depends(get_session),
):
    """
    API endpoint that dumps all users as CSV.
    """
    statement = select(UserModel).options(selectinload(UserModel.discord), selectinload(UserModel.ethics_form))
    data = session.exec(statement)

    # Initialize a StringIO object to write CSV data into memory
    output = StringIO()
    csv_writer = csv.writer(output)

    # Write the header row
    headers = [
        "Membership ID",
        "First Name",
        "Last Name",
        "NID",
        "Email",
        "Is Returning",
        "Is Member",
        "Gender",
        "Major",
        "Class Standing",
        "Shirt Size",
        "Discord Username",
        "Discord ID",
        "Experience",
        "Cyber Interests",
        "Event Interest",
        "Is C3 Interest",
        "Comments",
        "Ethics Form Timestamp",
        "Minecraft",
    ]
    csv_writer.writerow(headers)

    # Write user data rows
    for user in data:
        user_dict = user_to_dict(user)
        row = [
            user_dict.get("id"),
            user_dict.get("first_name"),
            user_dict.get("surname"),
            user_dict.get("nid"),
            user_dict.get("email"),
            user_dict.get("is_returning"),
            user_dict.get("is_full_member"),
            user_dict.get("gender"),
            user_dict.get("major"),
            user_dict.get("class_standing"),
            user_dict.get("shirt_size"),
            user_dict.get("discord", {}).get("username"),
            user_dict.get("discord", {}).get("id"),
            user_dict.get("experience"),
            user_dict.get("curiosity"),
            user_dict.get("attending"),
            user_dict.get("c3_interest"),
            user_dict.get("comments"),
            user_dict.get("ethics_form", {}).get("signtime"),
            user_dict.get("minecraft"),
        ]
        csv_writer.writerow(row)

    # Retrieve CSV content from StringIO and return as response
    csv_content = output.getvalue()
    output.close()

    return Response(content=csv_content, headers={"Content-Type": "text/csv"})


@router.post("/reset_memberships/")
async def reset_all_memberships(
    request: Request,
    current_admin: CurrentAdmin,
    session: Session = Depends(get_session),
):
    """
    API endpoint to reset all memberships and archive historical data.
    """
    # Parse request body
    body = await request.json()
    reset_reason = body.get("reset_reason", "Annual membership reset")

    # Get admin user info for logging
    admin_user_id = uuid.UUID(current_admin.get("id"))

    result = MembershipReset.reset_all_memberships(
        session=session,
        reset_reason=reset_reason,
        admin_user_id=admin_user_id,
    )

    return result


@router.get("/membership_history/")
async def get_membership_history(
    request: Request,
    current_admin: CurrentAdmin,
    user_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    """
    API endpoint to get membership history records.
    """
    history = MembershipReset.get_membership_history(
        session=session,
        user_id=user_id,
        limit=limit,
    )

    return {"data": history}


@router.get("/reset_summary/")
async def get_reset_summary(
    request: Request,
    current_admin: CurrentAdmin,
    session: Session = Depends(get_session),
):
    """
    API endpoint to get summary statistics about membership resets.
    """
    summary = MembershipReset.get_reset_summary(session=session)

    return {"data": summary}


@router.post("/restore_membership/")
async def restore_membership(
    request: Request,
    current_admin: CurrentAdmin,
    session: Session = Depends(get_session),
):
    """
    API endpoint to restore a user's membership from historical data.
    """
    # Parse request body
    body = await request.json()
    user_id = body.get("user_id")
    history_record_id = body.get("history_record_id")

    if not user_id or not history_record_id:
        return {"success": False, "error": "Missing user_id or history_record_id"}

    # Get admin user info for logging
    admin_user_id = uuid.UUID(current_admin.get("id"))

    result = MembershipReset.restore_membership_from_history(
        session=session,
        user_id=uuid.UUID(user_id),
        history_record_id=history_record_id,
        admin_user_id=admin_user_id,
    )

    return result


@router.post("/migrate_discord_account/")
async def migrate_discord_account(
    request: Request,
    current_admin: CurrentAdmin,
    old_user_id: uuid.UUID = Body(...),
    new_discord_id: str = Body(...),
    identity_verified: bool = Body(...),
    session: Session = Depends(get_session),
):
    """
    Execute Discord account migration with database transaction
    """

    if not identity_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identity verification is required")

    # Validate Discord ID format
    if not new_discord_id.isdigit() or len(new_discord_id) < 17 or len(new_discord_id) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Discord ID format")

    try:
        # Start database transaction
        with session.begin():
            # 1. Get old user account
            old_user = session.exec(
                select(UserModel)
                .where(UserModel.id == old_user_id)
                .options(
                    selectinload(UserModel.discord),
                    selectinload(UserModel.membership_history),
                )
            ).one_or_none()

            if not old_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Old user account not found")

            # 2. Check if account exists with new Discord ID
            new_user = session.exec(
                select(UserModel)
                .where(UserModel.discord_id == new_discord_id)
                .options(
                    selectinload(UserModel.discord),
                    selectinload(UserModel.ethics_form),
                    selectinload(UserModel.membership_history),
                )
            ).one_or_none()

            if not new_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No account found with Discord ID {new_discord_id}")

            # 3. Prevent migrating to self
            if old_user.discord_id == new_discord_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has this Discord ID")

            # 4. Store audit information for logging
            old_discord_id = old_user.discord_id
            admin_name = current_admin["name"]
            old_user_name = f"{old_user.first_name} {old_user.surname}"
            new_user_name = f"{new_user.first_name} {new_user.surname}"
            new_user_id = new_user.id

            # 5. Two-phase migration: delete temp user & flush, then reassign discord_id
            with session.no_autoflush:
                old_discord_model = old_user.discord
                new_discord_model = new_user.discord

                # Validate Case A invariant: both users must have discord models
                if not old_discord_model or not new_discord_model:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invariant violation: both source and target users must have discord profiles (Case A).")

                # Delete temp user's membership history (never preserve transient account history)
                if new_user.membership_history:
                    for mh in new_user.membership_history:
                        session.delete(mh)

                # Remove ethics form (transient)
                if new_user.ethics_form:
                    session.delete(new_user.ethics_form)

                # Merge new discord model fields into old discord model
                for attr in ["email", "mfa", "avatar", "banner", "color", "nitro", "locale", "username"]:
                    setattr(old_discord_model, attr, getattr(new_discord_model, attr))

                # Delete the new (now merged) discord model and the temp user
                session.delete(new_discord_model)
                session.delete(new_user)
                session.flush()

                # Update old user's discord_id AFTER freeing it from temp account
                old_user.discord_id = new_discord_id

                session.flush()
                session.refresh(old_user)

        # Transaction completed successfully - log the migration
        logger.info(
            f"Discord migration completed by admin {admin_name} ({current_admin['id']}): "
            f"User '{old_user_name}' ({old_user_id}) migrated from Discord {old_discord_id} to {new_discord_id}. "
            f"Temporary account '{new_user_name}' ({new_user_id}) was deleted."
        )

        return {
            "success": True,
            "message": f"Successfully migrated user to Discord ID {new_discord_id}",
            "old_discord_id": old_discord_id,
            "new_discord_id": new_discord_id,
            "user_id": str(old_user_id),
            "new_discord_username": old_user.discord.username if old_user.discord else "Unknown",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Discord migration failed for user {old_user_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Migration failed: {str(e)}")

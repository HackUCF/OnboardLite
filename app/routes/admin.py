# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import csv
import logging
import uuid
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.templating import Jinja2Templates
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


@router.get("/infra/")
async def get_infra(
    request: Request,
    current_admin: CurrentAdmin,
    member_id: Optional[uuid.UUID] = None,
    session: Session = Depends(get_session),
):
    """
    API endpoint to FORCE-provision Infra credentials (even without membership!!!)
    """

    if member_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing member_id parameter")

    user_data = session.exec(select(UserModel).where(UserModel.id == member_id)).one_or_none()

    creds = Approve.provision_infra(member_id, user_data)

    if creds is None:
        creds = {}

    if not creds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get user data

    # Send DM...
    new_creds_msg = load_and_render_template("app/messages/manual_invite_creds.md", user_data=user_data, creds=creds, settings=Settings())
    logger.debug(f"Rendered message: {new_creds_msg}")

    # Send Discord message
    Discord.send_message(user_data.discord_id, new_creds_msg)
    Email.send_email("Hack@UCF Private Cloud Credentials", new_creds_msg, user_data.email)
    return {
        "username": creds.get("username"),
        "password": creds.get("password"),
    }


@router.get("/refresh/")
async def get_refresh(
    request: Request,
    current_admin: CurrentAdmin,
    member_id: Optional[uuid.UUID] = None,
    session: Session = Depends(get_session),
):
    """
    API endpoint that re-runs the member verification workflow
    """
    if member_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing member_id parameter")

    Approve.approve_member(member_id)

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

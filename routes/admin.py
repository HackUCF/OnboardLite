from collections import OrderedDict
from typing import Optional

import boto3
from fastapi import APIRouter, Cookie, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.templating import Jinja2Templates
from jose import jwt

from models.user import UserModelMutable
from util.authentication import Authentication
from util.errors import Errors
from util.options import Options

options = Options.fetch()

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/admin", tags=["Admin"], responses=Errors.basic_http())


"""
Renders the Admin home page.
"""


@router.get("/")
@Authentication.admin
async def admin(request: Request, token: Optional[str] = Cookie(None)):
    payload = jwt.decode(
        token,
        options.get("jwt").get("secret"),
        algorithms=options.get("jwt").get("algorithm"),
    )
    return templates.TemplateResponse(
        "admin_searcher.html",
        {
            "request": request,
            "icon": payload["pfp"],
            "name": payload["name"],
            "id": payload["id"],
        },
    )


"""
API endpoint that gets a specific user's data as JSON
"""


@router.get("/get/")
@Authentication.admin
async def admin_get_single(
    request: Request,
    token: Optional[str] = Cookie(None),
    member_id: Optional[str] = "FAIL",
):
    if member_id == "FAIL":
        return {"data": {}, "error": "Missing ?member_id"}

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.get_item(Key={"id": member_id}).get("Item", None)

    if not data:
        return Errors.generate(request, 404, "User Not Found")

    return {"data": data}


"""
API endpoint that modifies a given user's data
"""


@router.post("/get/")
@Authentication.admin
async def admin_edit(
    request: Request,
    token: Optional[str] = Cookie(None),
    input_data: Optional[UserModelMutable] = {},
):
    member_id = input_data.id

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    old_data = table.get_item(Key={"id": member_id}).get("Item", None)

    if not old_data:
        return Errors.generate(request, 404, "User Not Found")

    # Take Pydantic data -> dict -> strip null values
    new_data = {k: v for k, v in jsonable_encoder(input_data).items() if v is not None}

    # Existing  U  Provided
    union = {**old_data, **new_data}

    # This is how this works:
    # 1. Get old data
    # 2. Get new data (pydantic-validated)
    # 3. Union the two
    # 4. Put back as one giant entry

    table.put_item(Item=union)

    return {"data": union, "msg": "Updated successfully!"}


"""
API endpoint that dumps all users as JSON.
"""


@router.get("/list")
@Authentication.admin
async def admin_list(request: Request, token: Optional[str] = Cookie(None)):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.scan().get("Items", None)
    return {"data": data}


"""
API endpoint that dumps all users as CSV.
"""


@router.get("/csv")
@Authentication.admin
async def admin_csv(request: Request, token: Optional[str] = Cookie(None)):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))
    data = table.scan().get("Items", None)

    # TODO: Instead of manually creating the CSV,
    #       use the CSV module to do it for us along with the User model.
    output = ""
    for user in data:
        fields = OrderedDict(
            {
                "Membership ID": user.get("id"),
                "First Name": user.get("first_name"),
                "Last Name": user.get("surname"),
                "NID": user.get("nid"),
                "Is Returning": user.get("is_returning"),
                "Gender": user.get("gender"),
                "Major": user.get("major"),
                "Class Standing": user.get("class_standing"),
                "Shirt Size": user.get("shirt_size"),
                "Discord Username": user.get("discord", {}).get("username"),
                "Experience": user.get("experience"),
                "Cyber Interests": user.get("curiosity"),
                "Event Interest": user.get("attending"),
                "Is C3 Interest": user.get("c3_interest"),
                "Comments": user.get("comments"),
                "Ethics Form Timestamp": user.get("ethics_form", {}).get("signtime"),
                "Minecraft": user.get("minecraft"),
                "Infra Email": user.get("infra_email"),
            }
        )

        if output == "":
            output += ", ".join(fields.keys()) + "\n"

        for field in fields.values():
            output += f'"{field}", '

        output += "\n"

    return Response(content=output, headers={"Content-Type": "text/csv"})

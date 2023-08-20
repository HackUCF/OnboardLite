from typing import Optional

import boto3
from fastapi import APIRouter, Cookie, Request
from fastapi.responses import HTMLResponse
from pydantic import error_wrappers

from models.info import InfoModel
from models.user import PublicContact
from util.authentication import Authentication
from util.errors import Errors
from util.kennelish import Kennelish, Transformer
from util.options import Options

options = Options.fetch()

router = APIRouter(prefix="/api", tags=["API"], responses=Errors.basic_http())


"""
Get API information.
"""


@router.get("/")
async def get_root():
    return InfoModel(
        name="Onboard (beta)",
        description="Hack@UCF's in-house membership management suite.",
        credits=[
            PublicContact(
                first_name="Jeffrey",
                surname="DiVincent",
                ops_email="jdivincent@hackucf.org",
            )
        ],
    )


@router.get("/form/{num}")
async def get_form(num: str):
    """
    Gets the JSON markup for a Kennelish file.
    For client-side rendering (if that ever becomes a thing).
    Note that Kennelish form files are NOT considered sensitive.
    """
    return Options.get_form_body(num)




@router.get("/form/{num}/html", response_class=HTMLResponse)
@Authentication.member
async def get_form_html(
    request: Request,
    token: Optional[str] = Cookie(None),
    payload: Optional[object] = {},
    num: str = 1,
):
    """
    Renders a Kennelish form file as HTML (with user data).
    Intended for AJAX applications.
    """
    # AWS dependencies
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    # Get form object
    data = Options.get_form_body(num)

    # Get data from DynamoDB
    user_data = table.get_item(Key={"id": payload.get("id")}).get("Item", None)

    # Have Kennelish parse the data.
    body = Kennelish.parse(data, user_data)

    return body




@router.post("/form/{num}")
@Authentication.member
async def post_form(
    request: Request,
    payload: Optional[object] = {},
    num: str = 1,
):
    """
    Allows updating the user's database using a schema assumed by the Kennelish file.
    """
    # Get Kennelish data
    kennelish_data = Options.get_form_body(num)
    model = Transformer.kennelish_to_pydantic(kennelish_data)

    try:
        inp = await request.json()
    except:
        return {"description": "Malformed JSON input."}

    try:
        validated = model(**inp)
    except error_wrappers.ValidationError:
        return {"description": "Malformed input."}

    # Remove items we did not update
    items_to_update = list(validated.dict().items())
    items_to_keep = []
    for item in items_to_update:
        if item[1] is not None:
            # English -> Boolean
            if item[1] == "Yes" or item[1] == "I promise not to do this.":
                item = (item[0], True)
            elif (
                item[1] == "No"
                or item[1]
                == "I disagree with this and do not wish to be part of Hack@UCF"
            ):
                item = (item[0], False)

            items_to_keep.append(item)

    update_expression = "SET "
    expression_attribute_values = {}

    # Here, the variable 'items_to_keep' is validated input.
    # We can update the user's profile from here.
    # TODO - I don't think this comment is accurate for a print statement
    print(items_to_keep)

    # Prepare to update to DynamoDB
    for item in items_to_keep:
        update_expression += f"{item[0]} = :{item[0].replace('.', '_')}, "
        expression_attribute_values[f":{item[0].replace('.', '_')}"] = item[1]

    # Strip last comma for update_expression
    update_expression = update_expression[:-2]

    # AWS dependencies
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(options.get("aws").get("dynamodb").get("table"))

    # Push data back to DynamoDB
    table.update_item(
        Key={"id": payload.get("id")},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values,
    )

    return validated

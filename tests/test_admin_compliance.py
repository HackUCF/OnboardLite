# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import UserModel
from app.util.auth_dependencies import Authentication
from app.util.forms import FORM_CORRECT_ANSWERS, Forms, iter_form_elements

FORM = "admin_compliance"
ANSWERS = FORM_CORRECT_ANSWERS[FORM]


@pytest.mark.parametrize("num", list(FORM_CORRECT_ANSWERS))
def test_answer_key_matches_form_options(num):
    # Radios validate as Literal[options], so a key that drifts from the form
    # text makes the quiz impossible to pass.
    options = {el["key"]: el.get("options", []) for el in iter_form_elements(Forms.get_form_body(num)) if el.get("key")}
    for key, answer in FORM_CORRECT_ANSWERS[num].items():
        assert key in options, f"{key} not in form {num}"
        assert answer in options[key], f"answer for {key} is not one of its options"


@pytest.fixture(name="untrained_admin_jwt")
def untrained_admin_jwt_fixture(session: Session, admin_user: UserModel):
    admin_user.admin_compliance_signtime = 0
    session.add(admin_user)
    session.commit()
    return Authentication.create_jwt(admin_user)


def test_untrained_admin_is_redirected_from_panel(client: TestClient, untrained_admin_jwt: str):
    response = client.get("/admin/", cookies={"token": untrained_admin_jwt}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/join/admin_compliance/"


@pytest.mark.parametrize("path", ["/admin/list", "/admin/csv", "/admin/payments/", "/admin/membership_history/"])
def test_untrained_admin_is_blocked_from_apis(client: TestClient, untrained_admin_jwt: str, path: str):
    response = client.get(path, cookies={"token": untrained_admin_jwt})
    assert response.status_code == 403


def test_wrong_answer_names_the_question(client: TestClient, session: Session, admin_user: UserModel, untrained_admin_jwt: str):
    body = {**ANSWERS, "admin_compliance_peer_ack": "Share it whenever it's a fellow officer/director asking; they're basically all trusted anyway."}
    response = client.post(f"/api/form/{FORM}", cookies={"token": untrained_admin_jwt}, json=body)
    assert response.status_code == 422
    assert "Scenario 5" in response.json()["detail"]
    assert "Scenario 1" not in response.json()["detail"]

    session.refresh(admin_user)
    assert not admin_user.admin_compliance_signtime


def test_passing_unlocks_panel_and_stamps_signtime_server_side(client: TestClient, session: Session, admin_user: UserModel, untrained_admin_jwt: str):
    # No signature time in the body: the server sets it on a pass.
    response = client.post(f"/api/form/{FORM}", cookies={"token": untrained_admin_jwt}, json=ANSWERS)
    assert response.status_code == 200

    session.refresh(admin_user)
    assert admin_user.admin_compliance_signtime > 1
    assert admin_user.admin_compliance_peer_ack is True

    assert client.get("/admin/list", cookies={"token": untrained_admin_jwt}).status_code == 200

    # Revisiting the form shows the passed answers selected.
    page = client.get(f"/join/{FORM}/", cookies={"token": untrained_admin_jwt})
    assert page.text.count("checked") == len(ANSWERS)

# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import uuid

import pytest
import stripe
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app, get_session
from app.models.user import DiscordModel, UserModel
from app.util.auth_dependencies import Authentication


@pytest.fixture(name="engine")
def engine_fixture():
    url = "sqlite://"
    engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    test_user_discord = DiscordModel(
        id=1,
        email="test_user@example.com",
        mfa=False,
        banner="https://upload.wikimedia.org/wikipedia/commons/e/e1/Banner_on_Wikivoyage.png",
        avatar="https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Style_-_Wouldn%27t_It_Be_Nice.png/600px-Style_-_Wouldn%27t_It_Be_Nice.png",
        color="1738207",
        nitro=False,
        locale="en_US",
        username="test_user",
    )
    test_user = UserModel(
        id=uuid.uuid4(),
        discord_id="123456123456123456",
        ucf_id=123456,
        nid="ko123456",
        ops_email="ops_test@example.com",
        infra_email="infra_test@example.com",
        minecraft="test_minecraft",
        github="test_github",
        first_name="Test",
        surname="User",
        email="test_user@example.com",
        is_returning=False,
        gender="M",
        major="Computer Science",
        class_standing="Senior",
        shirt_size="M",
        did_get_shirt=False,
        phone_number=1234567890,
        sudo=False,
        did_pay_dues=False,
        mentor_name="Test Mentor",
        is_full_member=True,
        can_vote=False,
        experience=1,
        curiosity="Very curious",
        c3_interest=False,
        attending="Yes",
        comments="Test comments",
        discord=test_user_discord,
    )
    session.add(test_user)
    session.commit()
    return test_user


@pytest.fixture(name="jwt")
def jwt_fixture(test_user: UserModel):
    return Authentication.create_jwt(test_user)


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    admin_discord = DiscordModel(
        id=2,
        email="admin@example.com",
        mfa=True,
        avatar="https://example.com/admin.png",
        color="0",
        nitro=False,
        locale="en_US",
        username="admin_user",
    )
    admin = UserModel(
        id=uuid.uuid4(),
        discord_id="999999999999999999",
        ucf_id=999999,
        nid="ad999999",
        first_name="Admin",
        surname="User",
        email="admin@example.com",
        shirt_size="L",
        sudo=True,
        did_pay_dues=True,
        is_full_member=True,
        discord=admin_discord,
    )
    session.add(admin)
    session.commit()
    return admin


@pytest.fixture(name="admin_jwt")
def admin_jwt_fixture(admin_user: UserModel):
    return Authentication.create_jwt(admin_user)


def make_checkout_session(id="cs_test_123", customer_email=None, metadata=None, amount_total=1000, currency="usd", payment_status="paid"):
    """
    Build a real ``stripe.checkout.Session`` from a raw payload, exactly as
    ``stripe.Webhook.construct_event`` does in the webhook route.

    Deliberately not a hand-rolled namespace. ``StripeObject`` is not a dict —
    it has no ``.get()`` — and because it defines ``__getattr__`` no type
    checker will flag the difference. A dict-based stand-in therefore accepts
    calls that raise ``AttributeError`` against the real object in production.
    """
    payload = {
        "id": id,
        "object": "checkout.session",
        "customer_email": customer_email,
        "metadata": metadata if metadata is not None else {},
        "amount_total": amount_total,
        "currency": currency,
        "payment_status": payment_status,
    }
    return stripe.checkout.Session.construct_from(payload, None)


@pytest.fixture(name="checkout_session_factory")
def checkout_session_factory_fixture():
    return make_checkout_session

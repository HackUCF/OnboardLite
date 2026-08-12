# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging

# Create the database
from alembic import script
from alembic.runtime import migration
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.util.settings import Settings

DATABASE_URL = Settings().database.url
logger = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    # echo=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Prod runs multiple uvicorn workers against one SQLite file, so both of these
# are about surviving concurrent access. Set per connection, since busy_timeout
# does not persist in the database file the way journal_mode does.
IS_SQLITE = engine.dialect.name == "sqlite"
IS_MEMORY_DB = ":memory:" in DATABASE_URL or DATABASE_URL in ("sqlite://", "sqlite:///")


@event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    if not IS_SQLITE:
        return
    cursor = dbapi_connection.cursor()
    try:
        # Wait for a held write lock instead of failing outright.
        cursor.execute("PRAGMA busy_timeout = 5000")
        # WAL lets readers carry on during a write. In-memory databases cannot
        # use it and have no other process to contend with anyway.
        if not IS_MEMORY_DB:
            cursor.execute("PRAGMA journal_mode = WAL")
    finally:
        cursor.close()


if "sqlite:///:memory:" in DATABASE_URL:
    SQLModel.metadata.create_all(engine)
    logger.info("Tables created in SQLite in-memory database.")


def init_db():
    return


def get_session():
    with Session(engine) as session:
        yield session


def check_current_head(alembic_cfg, connectable):
    # type: (config.Config, engine.Engine) -> bool
    # cfg = config.Config("../alembic.ini")
    directory = script.ScriptDirectory.from_config(alembic_cfg)
    with connectable.begin() as connection:
        context = migration.MigrationContext.configure(connection)
        return set(context.get_current_heads()) == set(directory.get_heads())

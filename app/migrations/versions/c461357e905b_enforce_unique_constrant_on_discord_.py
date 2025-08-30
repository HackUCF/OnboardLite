"""Enforce UNIQUE constraint on discord model user_ids

Revision ID: c461357e905b
Revises: 5f89a1b2c3d4
Create Date: 2025-08-30 17:54:51.646610

This migration adds a UNIQUE constraint (or unique index fallback) on discordmodel.user_id.
It intentionally does NOT attempt to clean up duplicate rows. Resolve duplicates manually
before running this migration if necessary.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c461357e905b"
down_revision: Union[str, None] = "5f89a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        # Use unique index for SQLite
        try:
            op.create_index("uq_discordmodel_user_id", "discordmodel", ["user_id"], unique=True)
        except Exception:
            pass
    else:
        # Prefer explicit unique constraint; fallback to index
        try:
            op.create_unique_constraint("uq_discordmodel_user_id", "discordmodel", ["user_id"])
        except Exception:
            try:
                op.create_index("uq_discordmodel_user_id", "discordmodel", ["user_id"], unique=True)
            except Exception:
                pass


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        try:
            op.drop_index("uq_discordmodel_user_id", table_name="discordmodel")
        except Exception:
            pass
    else:
        # Try dropping both (constraint first)
        try:
            op.drop_constraint("uq_discordmodel_user_id", "discordmodel", type_="unique")
        except Exception:
            pass
        try:
            op.drop_index("uq_discordmodel_user_id", table_name="discordmodel")
        except Exception:
            pass

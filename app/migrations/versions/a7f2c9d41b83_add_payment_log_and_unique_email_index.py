"""Add payment audit log and partial unique index on email

Revision ID: a7f2c9d41b83
Revises: 914bb7ce5299
Create Date: 2026-08-11 00:00:00.000000

The email index is PARTIAL: UserModel.email defaults to "" and most existing
rows are blank, so a plain unique index would fail on the existing data. Blanks
stay exempt; real addresses become unique.

Batch mode is intentionally not used. Creating a new table and creating an index
on an existing table are both native SQLite operations; batch mode is only
required for ALTER/DROP COLUMN. (Note render_as_batch is absent from the online
path in env.py, so batch would not apply here anyway.)

Pre-flight before running this against a populated database:

    SELECT email, COUNT(*) c FROM usermodel
    WHERE email IS NOT NULL AND email != '' GROUP BY lower(email) HAVING c > 1;

A non-empty result means the index creation will fail. Resolve those duplicates
by hand first, as was done for discord_id in c461357e905b.
"""

from typing import Sequence, Union

import sqlalchemy as sa  # noqa: F401
import sqlmodel  # noqa: F401
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7f2c9d41b83"
down_revision: Union[str, None] = "914bb7ce5299"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "paymentmodel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("checkout_session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("customer_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("recorded_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["recorded_by_admin_id"], ["usermodel.id"], name="fk_paymentmodel_recorded_by_admin_id"),
        sa.ForeignKeyConstraint(["user_id"], ["usermodel.id"], name="fk_paymentmodel_user_id"),
        sa.PrimaryKeyConstraint("id", name="pk_paymentmodel"),
    )
    op.create_index("ix_paymentmodel_user_id", "paymentmodel", ["user_id"], unique=False)
    op.create_index("ix_paymentmodel_created_at", "paymentmodel", ["created_at"], unique=False)
    op.create_index("uq_paymentmodel_checkout_session_id", "paymentmodel", ["checkout_session_id"], unique=True)

    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        op.create_index(
            "uq_usermodel_email",
            "usermodel",
            ["email"],
            unique=True,
            sqlite_where=sa.text("email IS NOT NULL AND email != ''"),
        )
    else:
        op.create_index(
            "uq_usermodel_email",
            "usermodel",
            ["email"],
            unique=True,
            postgresql_where=sa.text("email IS NOT NULL AND email != ''"),
        )


def downgrade() -> None:
    op.drop_index("uq_usermodel_email", table_name="usermodel")
    op.drop_index("uq_paymentmodel_checkout_session_id", table_name="paymentmodel")
    op.drop_index("ix_paymentmodel_created_at", table_name="paymentmodel")
    op.drop_index("ix_paymentmodel_user_id", table_name="paymentmodel")
    op.drop_table("paymentmodel")

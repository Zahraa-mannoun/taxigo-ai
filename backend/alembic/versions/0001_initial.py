"""initial bookings table

Revision ID: 0001
Revises:
Create Date: 2026-07-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_name", sa.Text(), nullable=False),
        sa.Column("pickup", sa.Text(), nullable=False),
        sa.Column("dropoff", sa.Text(), nullable=False),
        sa.Column("trip_date", sa.Date(), nullable=False),
        sa.Column("trip_time", sa.Time(), nullable=False),
        sa.Column("fare", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="confirmed"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("reminded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_bookings_trip_date", "bookings", ["trip_date"])
    op.create_index("ix_bookings_status", "bookings", ["status"])
    op.create_index("ix_bookings_client_name", "bookings", ["client_name"])


def downgrade() -> None:
    op.drop_index("ix_bookings_client_name", table_name="bookings")
    op.drop_index("ix_bookings_status", table_name="bookings")
    op.drop_index("ix_bookings_trip_date", table_name="bookings")
    op.drop_table("bookings")

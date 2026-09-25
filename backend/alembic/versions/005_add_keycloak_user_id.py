"""Add keycloak_user_id column to users table.

Revision ID: 005_add_keycloak_user_id
Revises: 004_add_process_event_log
Create Date: 2026-09-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_add_keycloak_user_id"
down_revision: Union[str, None] = "004_add_process_event_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("keycloak_user_id", sa.String(length=255), nullable=True)
    )
    op.create_unique_constraint(
        "uq_users_keycloak_user_id",
        "users",
        ["keycloak_user_id"]
    )
    op.create_index(
        "ix_users_keycloak_user_id",
        "users",
        ["keycloak_user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_users_keycloak_user_id", table_name="users")
    op.drop_constraint("uq_users_keycloak_user_id", table_name="users", type_="unique")
    op.drop_column("users", "keycloak_user_id")

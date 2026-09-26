"""Add incident_attachments table.

Revision ID: 006_add_incident_attachments
Revises: 005_add_keycloak_user_id
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_add_incident_attachments"
down_revision: Union[str, None] = "005_add_keycloak_user_id"

branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incident_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incident_attachments_id"), "incident_attachments", ["id"], unique=False)
    op.create_index(op.f("ix_incident_attachments_incident_id"), "incident_attachments", ["incident_id"], unique=False)
    op.create_index(op.f("ix_incident_attachments_uploaded_by_id"), "incident_attachments", ["uploaded_by_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_incident_attachments_uploaded_by_id"), table_name="incident_attachments")
    op.drop_index(op.f("ix_incident_attachments_incident_id"), table_name="incident_attachments")
    op.drop_index(op.f("ix_incident_attachments_id"), table_name="incident_attachments")
    op.drop_table("incident_attachments")

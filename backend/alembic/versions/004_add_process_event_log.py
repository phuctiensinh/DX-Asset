"""Add structured process case and event log tables.

Revision ID: 004_add_process_event_log
Revises: 003_add_smart_routing_and_skills
Create Date: 2026-09-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_add_process_event_log"
down_revision: Union[str, None] = "003_add_smart_routing_and_skills"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "process_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_type", sa.String(length=20), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("maintenance_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "case_type IN ('INCIDENT', 'MAINTENANCE')",
            name="ck_process_cases_case_type",
        ),
        sa.CheckConstraint(
            "(incident_id IS NOT NULL AND maintenance_id IS NULL) OR "
            "(incident_id IS NULL AND maintenance_id IS NOT NULL)",
            name="ck_process_cases_exactly_one_entity",
        ),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["maintenance_id"], ["maintenances.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_id", name="uq_process_cases_incident_id"),
        sa.UniqueConstraint("maintenance_id", name="uq_process_cases_maintenance_id"),
    )

    op.create_table(
        "process_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("maintenance_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=True),
        sa.Column("performed_by_id", sa.Integer(), nullable=True),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("case_sequence", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("timestamp_quality", sa.String(length=20), nullable=False),
        sa.Column("source_event_key", sa.String(length=200), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('INCIDENT_CREATED', 'INCIDENT_STATUS_CHANGED', 'TECHNICIAN_ASSIGNED', "
            "'MAINTENANCE_CREATED', 'MAINTENANCE_STATUS_CHANGED')",
            name="ck_process_events_event_type",
        ),
        sa.CheckConstraint("source IN ('LIVE', 'BACKFILL')", name="ck_process_events_source"),
        sa.CheckConstraint(
            "timestamp_quality IN ('ACTION_TIME', 'LEGACY_FIELD', 'AMBIGUOUS')",
            name="ck_process_events_timestamp_quality",
        ),
        sa.CheckConstraint(
            "(event_type = 'INCIDENT_CREATED' AND from_status IS NULL AND to_status IS NOT NULL) OR "
            "(event_type IN ('INCIDENT_STATUS_CHANGED', 'MAINTENANCE_STATUS_CHANGED') "
            "AND from_status IS NOT NULL AND to_status IS NOT NULL) OR "
            "(event_type NOT IN ('INCIDENT_CREATED', 'INCIDENT_STATUS_CHANGED', 'MAINTENANCE_STATUS_CHANGED') "
            "AND from_status IS NULL AND to_status IS NULL)",
            name="ck_process_events_status_fields",
        ),
        sa.CheckConstraint("case_sequence > 0", name="ck_process_events_positive_sequence"),
        sa.ForeignKeyConstraint(["case_id"], ["process_cases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["maintenance_id"], ["maintenances.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["performed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "case_sequence", name="uq_process_events_case_sequence"),
        sa.UniqueConstraint("source_event_key", name="uq_process_events_source_event_key"),
    )

    op.create_index(
        "ix_process_events_case_time_sequence",
        "process_events",
        ["case_id", "occurred_at", "case_sequence"],
    )
    op.create_index("ix_process_events_time_case", "process_events", ["occurred_at", "case_id"])
    op.create_index("ix_process_events_type_time", "process_events", ["event_type", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_process_events_type_time", table_name="process_events")
    op.drop_index("ix_process_events_time_case", table_name="process_events")
    op.drop_index("ix_process_events_case_time_sequence", table_name="process_events")
    op.drop_table("process_events")
    op.drop_table("process_cases")

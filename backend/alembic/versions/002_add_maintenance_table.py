"""Add maintenance table for Phase 10

Revision ID: 002_add_maintenance_table
Revises: 001_initial_schema
Create Date: 2026-09-19 21:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_add_maintenance_table'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'maintenances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('maintenance_code', sa.String(length=50), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('incident_id', sa.Integer(), nullable=True),
        sa.Column('technician_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('repair_cost', sa.Numeric(precision=12, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['technician_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('maintenance_code')
    )
    op.create_index(op.f('ix_maintenances_asset_id'), 'maintenances', ['asset_id'], unique=False)
    op.create_index(op.f('ix_maintenances_incident_id'), 'maintenances', ['incident_id'], unique=False)
    op.create_index(op.f('ix_maintenances_technician_id'), 'maintenances', ['technician_id'], unique=False)
    op.create_index(op.f('ix_maintenances_status'), 'maintenances', ['status'], unique=False)
    op.create_index(op.f('ix_maintenances_id'), 'maintenances', ['id'], unique=False)
    op.create_index(op.f('ix_maintenances_maintenance_code'), 'maintenances', ['maintenance_code'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_maintenances_maintenance_code'), table_name='maintenances')
    op.drop_index(op.f('ix_maintenances_id'), table_name='maintenances')
    op.drop_index(op.f('ix_maintenances_status'), table_name='maintenances')
    op.drop_index(op.f('ix_maintenances_technician_id'), table_name='maintenances')
    op.drop_index(op.f('ix_maintenances_incident_id'), table_name='maintenances')
    op.drop_index(op.f('ix_maintenances_asset_id'), table_name='maintenances')
    op.drop_table('maintenances')

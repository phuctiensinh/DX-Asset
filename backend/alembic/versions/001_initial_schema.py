"""Initial database schema migration for DX-Asset

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-18 19:42:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create departments table
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_departments_code'), 'departments', ['code'], unique=True)
    op.create_index(op.f('ix_departments_id'), 'departments', ['id'], unique=False)

    # 2. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_department_id'), 'users', ['department_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)

    # 3. Create assets table
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('brand', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=50), nullable=True),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('warranty_expiry', sa.Date(), nullable=True),
        sa.Column('current_user_id', sa.Integer(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('qr_code_url', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['current_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_code'),
        sa.UniqueConstraint('serial_number')
    )
    op.create_index(op.f('ix_assets_asset_code'), 'assets', ['asset_code'], unique=True)
    op.create_index(op.f('ix_assets_category'), 'assets', ['category'], unique=False)
    op.create_index(op.f('ix_assets_current_user_id'), 'assets', ['current_user_id'], unique=False)
    op.create_index(op.f('ix_assets_department_id'), 'assets', ['department_id'], unique=False)
    op.create_index(op.f('ix_assets_id'), 'assets', ['id'], unique=False)
    op.create_index(op.f('ix_assets_serial_number'), 'assets', ['serial_number'], unique=True)
    op.create_index(op.f('ix_assets_status'), 'assets', ['status'], unique=False)

    # 4. Create asset_assignments table
    op.create_table(
        'asset_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('assigned_to_user_id', sa.Integer(), nullable=False),
        sa.Column('assigned_by_user_id', sa.Integer(), nullable=False),
        sa.Column('assigned_date', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('return_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['assigned_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asset_assignments_asset_id'), 'asset_assignments', ['asset_id'], unique=False)
    op.create_index(op.f('ix_asset_assignments_assigned_to_user_id'), 'asset_assignments', ['assigned_to_user_id'], unique=False)
    op.create_index(op.f('ix_asset_assignments_id'), 'asset_assignments', ['id'], unique=False)
    op.create_index(op.f('ix_asset_assignments_status'), 'asset_assignments', ['status'], unique=False)

    # PostgreSQL Partial Unique Index: Only ONE active assignment per asset
    op.create_index(
        'uq_active_asset_assignment',
        'asset_assignments',
        ['asset_id'],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'")
    )

    # 5. Create incidents table
    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_code', sa.String(length=50), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('reporter_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('assigned_it_id', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('repair_cost', sa.Numeric(precision=12, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['assigned_it_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_code')
    )
    op.create_index(op.f('ix_incidents_asset_id'), 'incidents', ['asset_id'], unique=False)
    op.create_index(op.f('ix_incidents_assigned_it_id'), 'incidents', ['assigned_it_id'], unique=False)
    op.create_index(op.f('ix_incidents_category'), 'incidents', ['category'], unique=False)
    op.create_index(op.f('ix_incidents_id'), 'incidents', ['id'], unique=False)
    op.create_index(op.f('ix_incidents_priority'), 'incidents', ['priority'], unique=False)
    op.create_index(op.f('ix_incidents_reporter_id'), 'incidents', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_incidents_status'), 'incidents', ['status'], unique=False)
    op.create_index(op.f('ix_incidents_ticket_code'), 'incidents', ['ticket_code'], unique=True)

    # 6. Create asset_histories table
    op.create_table(
        'asset_histories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('performed_by_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['performed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asset_histories_action_type'), 'asset_histories', ['action_type'], unique=False)
    op.create_index(op.f('ix_asset_histories_asset_id'), 'asset_histories', ['asset_id'], unique=False)
    op.create_index(op.f('ix_asset_histories_id'), 'asset_histories', ['id'], unique=False)
    op.create_index(op.f('ix_asset_histories_performed_by_id'), 'asset_histories', ['performed_by_id'], unique=False)


def downgrade() -> None:
    op.drop_table('asset_histories')
    op.drop_table('incidents')
    op.drop_index('uq_active_asset_assignment', table_name='asset_assignments', postgresql_where=sa.text("status = 'ACTIVE'"))
    op.drop_table('asset_assignments')
    op.drop_table('assets')
    op.drop_table('users')
    op.drop_table('departments')

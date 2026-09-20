"""Add technician_skills table and smart routing metadata columns for Phase 11

Revision ID: 003_add_smart_routing_and_skills
Revises: 002_add_maintenance_table
Create Date: 2026-09-20 16:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_add_smart_routing_and_skills'
down_revision: Union[str, None] = '002_add_maintenance_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create technician_skills table
    op.create_table(
        'technician_skills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('skill_level', sa.Integer(), nullable=False, server_default=sa.text('3')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'category', name='uq_technician_skill_user_category')
    )
    op.create_index(op.f('ix_technician_skills_id'), 'technician_skills', ['id'], unique=False)
    op.create_index(op.f('ix_technician_skills_user_id'), 'technician_skills', ['user_id'], unique=False)
    op.create_index(op.f('ix_technician_skills_category'), 'technician_skills', ['category'], unique=False)

    # 2. Add smart routing metadata columns to incidents table
    op.add_column('incidents', sa.Column('suggested_queue', sa.String(length=50), nullable=True))
    op.add_column('incidents', sa.Column('ai_confidence', sa.Float(), nullable=True))
    op.add_column('incidents', sa.Column('ai_reasoning', sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('incidents', 'ai_reasoning')
    op.drop_column('incidents', 'ai_confidence')
    op.drop_column('incidents', 'suggested_queue')

    op.drop_index(op.f('ix_technician_skills_category'), table_name='technician_skills')
    op.drop_index(op.f('ix_technician_skills_user_id'), table_name='technician_skills')
    op.drop_index(op.f('ix_technician_skills_id'), table_name='technician_skills')
    op.drop_table('technician_skills')

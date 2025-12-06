"""Add UserModuleDOT table for module-specific DOT assignments

Revision ID: a1b2c3d4e5f6
Revises: 0b33abb2a8e9
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '0b33abb2a8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_module_dots table
    op.create_table(
        'user_module_dots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('dot_id', sa.Integer(), nullable=False),
        sa.Column('module', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['dot_id'], ['dots.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'module', name='uq_user_module_dot')
    )
    op.create_index(op.f('ix_user_module_dots_user_id'), 'user_module_dots', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_module_dots_dot_id'), 'user_module_dots', ['dot_id'], unique=False)
    op.create_index(op.f('ix_user_module_dots_module'), 'user_module_dots', ['module'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_module_dots_module'), table_name='user_module_dots')
    op.drop_index(op.f('ix_user_module_dots_dot_id'), table_name='user_module_dots')
    op.drop_index(op.f('ix_user_module_dots_user_id'), table_name='user_module_dots')
    op.drop_table('user_module_dots')



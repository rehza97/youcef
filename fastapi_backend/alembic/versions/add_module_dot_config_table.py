"""add module_dot_config table

Revision ID: add_module_dot_config
Revises: a1b2c3d4e5f6
Create Date: 2024-12-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_module_dot_config'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create module_dot_config table for system-level default DOT assignments per module.

    This enables setting a default DOT for each module that will be used when:
    1. No user-specific module DOT is assigned
    2. Before falling back to the global user.dot_id
    """
    op.create_table(
        'module_dot_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('module', sa.String(length=100), nullable=False),
        sa.Column('dot_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['dot_id'], ['dots.dot_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('module', name='uq_module_dot_config_module')
    )

    # Create indexes for better query performance
    op.create_index('ix_module_dot_config_id', 'module_dot_config', ['id'])
    op.create_index('ix_module_dot_config_module', 'module_dot_config', ['module'])
    op.create_index('ix_module_dot_config_dot_id', 'module_dot_config', ['dot_id'])


def downgrade():
    """
    Drop module_dot_config table and its indexes.
    """
    op.drop_index('ix_module_dot_config_dot_id', table_name='module_dot_config')
    op.drop_index('ix_module_dot_config_module', table_name='module_dot_config')
    op.drop_index('ix_module_dot_config_id', table_name='module_dot_config')
    op.drop_table('module_dot_config')

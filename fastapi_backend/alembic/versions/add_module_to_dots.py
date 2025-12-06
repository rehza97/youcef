"""add module to dots table

Revision ID: add_module_to_dots
Revises: add_module_dot_config
Create Date: 2024-12-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_module_to_dots'
down_revision = 'add_module_dot_config'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add module column to dots table to support module-specific DOTs.

    This allows having separate DOT records for each module.
    For example: 4 separate "Alger" DOTs - one for each module.
    """
    # Add module column
    op.add_column('dots', sa.Column('module', sa.String(length=100), nullable=True))

    # Create index on module column
    op.create_index('ix_dots_module', 'dots', ['module'])

    # Drop the old unique constraint on name only
    op.drop_constraint('dots_name_key', 'dots', type_='unique')

    # Create new unique constraint on (name, module) combination
    op.create_unique_constraint('uq_dot_name_module', 'dots', ['name', 'module'])


def downgrade():
    """
    Remove module column and restore original unique constraint.
    """
    # Drop the new unique constraint
    op.drop_constraint('uq_dot_name_module', 'dots', type_='unique')

    # Restore old unique constraint on name only
    op.create_unique_constraint('dots_name_key', 'dots', ['name'])

    # Drop index
    op.drop_index('ix_dots_module', table_name='dots')

    # Drop module column
    op.drop_column('dots', 'module')

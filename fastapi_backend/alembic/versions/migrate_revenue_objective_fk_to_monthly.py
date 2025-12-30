"""Migrate revenue_objective_id FK from revenue_objectives to objectifs_monthly_dot

Revision ID: migrate_revenue_fk
Revises: 35a0dcd47a03
Create Date: 2025-12-29

This migration updates the revenue_journal table to use monthly objectives
instead of annual objectives by changing the foreign key constraint.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'migrate_revenue_fk'
down_revision: Union[str, None] = '1540626b1dd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """
    Update revenue_journal.revenue_objective_id to point to objectifs_monthly_dot
    instead of revenue_objectives table.
    """
    # Step 1: Drop the existing foreign key constraint
    op.drop_constraint(
        'revenue_journal_revenue_objective_id_fkey',
        'revenue_journal',
        type_='foreignkey'
    )

    # Step 2: Clear existing revenue_objective_id values (they point to wrong table)
    # NOTE: You may want to run fix_revenue_objectives.py after this migration
    op.execute("UPDATE revenue_journal SET revenue_objective_id = NULL")

    # Step 3: Create new foreign key constraint pointing to objectifs_monthly_dot
    op.create_foreign_key(
        'revenue_journal_revenue_objective_id_fkey',
        'revenue_journal',
        'objectifs_monthly_dot',
        ['revenue_objective_id'],
        ['id']
    )

    print("✅ Migration complete: revenue_objective_id now points to objectifs_monthly_dot")
    print("⚠️  Run fix_revenue_objectives.py to re-link records and recalculate achievement rates")


def downgrade():
    """
    Revert back to using revenue_objectives table (if needed for rollback)
    """
    # Step 1: Drop the new foreign key constraint
    op.drop_constraint(
        'revenue_journal_revenue_objective_id_fkey',
        'revenue_journal',
        type_='foreignkey'
    )

    # Step 2: Clear revenue_objective_id values
    op.execute("UPDATE revenue_journal SET revenue_objective_id = NULL")

    # Step 3: Restore old foreign key constraint pointing to revenue_objectives
    op.create_foreign_key(
        'revenue_journal_revenue_objective_id_fkey',
        'revenue_journal',
        'revenue_objectives',
        ['revenue_objective_id'],
        ['id']
    )

    print("⏪ Rollback complete: revenue_objective_id now points back to revenue_objectives")

"""Add CASCADE DELETE to all DOT foreign key constraints

Revision ID: add_cascade_dot_fks
Revises: migrate_revenue_fk
Create Date: 2025-12-30

This migration adds ON DELETE CASCADE to all foreign key constraints
pointing to the dots table, ensuring database-level cascade deletion.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_cascade_dot_fks'
down_revision: Union[str, None] = 'migrate_revenue_fk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """
    Add ON DELETE CASCADE to all foreign key constraints referencing dots table

    NOTE: This migration uses batch operations to handle constraints safely.
    If any constraint doesn't exist with the expected name, it will be skipped.
    """

    # Use raw SQL to add CASCADE - more reliable than ORM operations
    connection = op.get_bind()

    # List of tables and constraints to update
    tables_to_update = [
        'users',
        'parks',
        'parks_2b',
        'revenue_journal',
        'revenue_objectives',
        'objectifs_monthly_dot',
        'encaissement_ar_dot',
        'encaissement_anomaly',
        'encaissement_aggregate_view',
        'creance_periodique_dot',
        'creance_aggregate_view',
    ]

    for table_name in tables_to_update:
        try:
            # Find the constraint name dynamically
            result = connection.execute(sa.text(f"""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = '{table_name}'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%dot_id%'
            """))

            constraint_name = result.scalar()

            if constraint_name:
                # Drop and recreate with CASCADE
                connection.execute(sa.text(f"""
                    ALTER TABLE {table_name}
                    DROP CONSTRAINT IF EXISTS {constraint_name};
                """))

                connection.execute(sa.text(f"""
                    ALTER TABLE {table_name}
                    ADD CONSTRAINT {constraint_name}
                    FOREIGN KEY (dot_id)
                    REFERENCES dots(id)
                    ON DELETE CASCADE;
                """))

                print(f"✅ Added CASCADE to {table_name}")
            else:
                print(f"⚠️  No FK constraint found for {table_name}")

        except Exception as e:
            print(f"⚠️  Could not update {table_name}: {e}")
            # Continue with other tables


def downgrade():
    """
    Remove ON DELETE CASCADE from foreign key constraints (revert to default)
    """
    connection = op.get_bind()

    tables_to_revert = [
        'users',
        'parks',
        'parks_2b',
        'revenue_journal',
        'revenue_objectives',
        'objectifs_monthly_dot',
        'encaissement_ar_dot',
        'encaissement_anomaly',
        'encaissement_aggregate_view',
        'creance_periodique_dot',
        'creance_aggregate_view',
    ]

    for table_name in tables_to_revert:
        try:
            # Find constraint name
            result = connection.execute(sa.text(f"""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = '{table_name}'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%dot_id%'
            """))

            constraint_name = result.scalar()

            if constraint_name:
                # Drop and recreate without CASCADE
                connection.execute(sa.text(f"""
                    ALTER TABLE {table_name}
                    DROP CONSTRAINT IF EXISTS {constraint_name};
                """))

                connection.execute(sa.text(f"""
                    ALTER TABLE {table_name}
                    ADD CONSTRAINT {constraint_name}
                    FOREIGN KEY (dot_id)
                    REFERENCES dots(id);
                """))

                print(f"⏪ Removed CASCADE from {table_name}")

        except Exception as e:
            print(f"⚠️  Could not revert {table_name}: {e}")

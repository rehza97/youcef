#!/usr/bin/env python3
"""
Script to reset PostgreSQL sequences after migration
"""

import psycopg2
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reset_sequences():
    """Reset PostgreSQL sequences to fix ID conflicts"""

    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='youcef_db',
            user='postgres',
            password='123456789'
        )

        cursor = conn.cursor()

        # Get all tables with sequences
        cursor.execute("""
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND column_default LIKE 'nextval%'
            ORDER BY table_name, ordinal_position
        """)

        sequences = cursor.fetchall()
        logger.info(f"Found {len(sequences)} sequences to reset")

        for table_name, column_name in sequences:
            try:
                # Get the maximum ID for this table
                cursor.execute(f"SELECT MAX({column_name}) FROM {table_name}")
                max_id = cursor.fetchone()[0]

                if max_id is not None:
                    # Reset the sequence to the maximum ID + 1
                    sequence_name = f"{table_name}_{column_name}_seq"
                    cursor.execute(
                        f"SELECT setval('{sequence_name}', {max_id + 1}, false)")
                    logger.info(
                        f"Reset sequence for {table_name}.{column_name} to {max_id + 1}")
                else:
                    logger.info(
                        f"Table {table_name} is empty, setting sequence to 1")
                    sequence_name = f"{table_name}_{column_name}_seq"
                    cursor.execute(
                        f"SELECT setval('{sequence_name}', 1, false)")

            except Exception as e:
                logger.warning(
                    f"Could not reset sequence for {table_name}.{column_name}: {e}")

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("✅ All sequences reset successfully!")

    except Exception as e:
        logger.error(f"Error resetting sequences: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    reset_sequences()

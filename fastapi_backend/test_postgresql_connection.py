#!/usr/bin/env python3
"""
Test PostgreSQL connection
"""

import psycopg2
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_connection():
    """Test PostgreSQL connection"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='youcef_db',
            user='postgres',
            password='123456789'
        )

        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()

        logger.info(f"Successfully connected to PostgreSQL: {version[0]}")

        # Test if tables exist
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Found {len(tables)} tables: {tables}")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False


if __name__ == "__main__":
    test_connection()

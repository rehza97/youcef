#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
import os
from core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLite database path
SQLITE_DB_PATH = "fastapi_backend.db"

# PostgreSQL connection details
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'youcef_db',
    'user': 'postgres',
    'password': '123456789'
}

# Define migration order to respect foreign key constraints
MIGRATION_ORDER = [
    'alembic_version',
    'roles',
    'permissions',
    'users',
    'user_roles',
    'role_permissions',
    'conversations',
    'conversation_participants',
    'notifications',
    'notification_preferences',
    'messages',
    'message_reactions',
    'user_blocks',
    'file_uploads',
    'file_previews'
]


def get_sqlite_connection():
    """Get SQLite connection"""
    if not os.path.exists(SQLITE_DB_PATH):
        logger.error(f"SQLite database file {SQLITE_DB_PATH} not found!")
        return None

    return sqlite3.connect(SQLITE_DB_PATH)


def get_postgresql_connection():
    """Get PostgreSQL connection"""
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return None


def get_table_names(sqlite_conn):
    """Get all table names from SQLite"""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def convert_boolean_columns(columns, rows):
    """Convert integer boolean columns to actual booleans"""
    boolean_columns = []
    for i, col in enumerate(columns):
        col_name = col[1].lower()
        if any(keyword in col_name for keyword in ['is_', 'has_', '_enabled', '_active', '_read', '_edited', '_admin']):
            boolean_columns.append(i)

    converted_rows = []
    for row in rows:
        new_row = list(row)
        for col_idx in boolean_columns:
            if new_row[col_idx] is not None:
                new_row[col_idx] = bool(new_row[col_idx])
        converted_rows.append(tuple(new_row))

    return converted_rows


def migrate_table(sqlite_conn, pg_conn, table_name):
    """Migrate a single table from SQLite to PostgreSQL"""
    try:
        # Get table structure from SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
        columns = sqlite_cursor.fetchall()

        # Get data from SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()

        if not rows:
            logger.info(f"Table {table_name} is empty, skipping...")
            return

        # Create table in PostgreSQL if it doesn't exist
        pg_cursor = pg_conn.cursor()

        # Generate CREATE TABLE statement
        column_definitions = []
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            col_not_null = "NOT NULL" if col[3] else ""
            col_pk = "PRIMARY KEY" if col[5] else ""

            # Map SQLite types to PostgreSQL types
            if col_type.upper() == "INTEGER":
                # Check if this is likely a boolean column
                col_name_lower = col_name.lower()
                if any(keyword in col_name_lower for keyword in ['is_', 'has_', '_enabled', '_active', '_read', '_edited', '_admin']):
                    pg_type = "BOOLEAN"
                else:
                    pg_type = "INTEGER"
            elif col_type.upper() == "TEXT":
                pg_type = "TEXT"
            elif col_type.upper() == "REAL":
                pg_type = "DOUBLE PRECISION"
            elif col_type.upper() == "BLOB":
                pg_type = "BYTEA"
            else:
                pg_type = col_type

            definition = f"{col_name} {pg_type} {col_not_null} {col_pk}".strip()
            column_definitions.append(definition)

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {', '.join(column_definitions)}
        );
        """

        pg_cursor.execute(create_table_sql)

        # Insert data
        if rows:
            # Get column names
            sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
            column_names = [col[1] for col in sqlite_cursor.fetchall()]

            # Convert boolean columns
            converted_rows = convert_boolean_columns(columns, rows)

            # Prepare INSERT statement with ON CONFLICT DO NOTHING
            placeholders = ', '.join(['%s'] * len(column_names))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

            # Insert data
            pg_cursor.executemany(insert_sql, converted_rows)

            logger.info(f"Migrated {len(rows)} rows from {table_name}")

        pg_conn.commit()
        pg_cursor.close()
        sqlite_cursor.close()

    except Exception as e:
        logger.error(f"Error migrating table {table_name}: {e}")
        pg_conn.rollback()


def clear_postgresql_tables(pg_conn):
    """Clear all tables in PostgreSQL to start fresh"""
    try:
        pg_cursor = pg_conn.cursor()

        # Disable foreign key checks temporarily
        pg_cursor.execute("SET session_replication_role = replica;")

        # Get all tables
        pg_cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename != 'spatial_ref_sys'
        """)
        tables = [row[0] for row in pg_cursor.fetchall()]

        # Clear tables in reverse order to avoid foreign key issues
        for table in reversed(tables):
            pg_cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
            logger.info(f"Cleared table: {table}")

        # Re-enable foreign key checks
        pg_cursor.execute("SET session_replication_role = DEFAULT;")
        pg_conn.commit()
        pg_cursor.close()

    except Exception as e:
        logger.error(f"Error clearing tables: {e}")
        pg_conn.rollback()


def main():
    """Main migration function"""
    logger.info("Starting migration from SQLite to PostgreSQL...")

    # Connect to SQLite
    sqlite_conn = get_sqlite_connection()
    if not sqlite_conn:
        return

    # Connect to PostgreSQL
    pg_conn = get_postgresql_connection()
    if not pg_conn:
        sqlite_conn.close()
        return

    try:
        # Clear existing data in PostgreSQL
        logger.info("Clearing existing PostgreSQL tables...")
        clear_postgresql_tables(pg_conn)

        # Get all tables
        tables = get_table_names(sqlite_conn)
        logger.info(f"Found {len(tables)} tables: {tables}")

        # Migrate each table in the correct order
        for table in MIGRATION_ORDER:
            if table in tables:
                logger.info(f"Migrating table: {table}")
                migrate_table(sqlite_conn, pg_conn, table)

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()

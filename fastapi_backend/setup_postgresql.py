#!/usr/bin/env python3
"""
Setup script for PostgreSQL database
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
import os
from core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_database():
    """Create the youcef_db database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server (not to a specific database)
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='123456789'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = conn.cursor()

        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname='youcef_db'")
        exists = cursor.fetchone()

        if not exists:
            cursor.execute("CREATE DATABASE youcef_db")
            logger.info("Database 'youcef_db' created successfully")
        else:
            logger.info("Database 'youcef_db' already exists")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Error creating database: {e}")
        logger.error("Please make sure PostgreSQL is running and accessible")
        logger.error("You may need to:")
        logger.error("1. Install PostgreSQL")
        logger.error("2. Start PostgreSQL service")
        logger.error("3. Update the password in the script if different")


def test_connection():
    """Test connection to the database"""
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

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False


def setup_environment():
    """Create .env file with PostgreSQL configuration"""
    env_content = """# PostgreSQL Database Configuration
DATABASE_URL=postgresql://postgres:123456789@localhost:5432/youcef_db

# Application Settings
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True

# Redis Configuration
REDIS_URL=redis://localhost:6379

# CORS Settings
CORS_ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]

# Rate Limiting
RATE_LIMIT_ANON=100/hour
RATE_LIMIT_USER=1000/hour
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_REGISTER=3/minute

# File Upload
MAX_FILE_SIZE=104857600
UPLOAD_DIR=uploads

# Logging
LOG_LEVEL=INFO
LOG_FILE=fastapi.log
"""

    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        logger.info("Created .env file with PostgreSQL configuration")
    except Exception as e:
        logger.error(f"Error creating .env file: {e}")


def main():
    """Main setup function"""
    logger.info("Setting up PostgreSQL for Youcef Backend...")

    # Create database
    create_database()

    # Test connection
    if test_connection():
        logger.info("PostgreSQL setup completed successfully!")

        # Setup environment file
        setup_environment()

        logger.info("\nNext steps:")
        logger.info(
            "1. Install PostgreSQL dependencies: pip install -r requirements.txt")
        logger.info(
            "2. Run the migration script: python migrate_to_postgresql.py")
        logger.info("3. Start the FastAPI server: python main.py")
    else:
        logger.error(
            "PostgreSQL setup failed. Please check your PostgreSQL installation.")


if __name__ == "__main__":
    main()

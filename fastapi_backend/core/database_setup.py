"""
Database setup utilities for automatic initialization
"""
import logging
import subprocess
import os
from pathlib import Path
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# Try to import psycopg2, but don't fail if it causes issues
try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    PSYCOPG2_AVAILABLE = True
except Exception as e:
    logger.warning(f"psycopg2 import failed: {e}")
    logger.warning("Automatic database creation will be disabled")
    PSYCOPG2_AVAILABLE = False
    psycopg2 = None
    ISOLATION_LEVEL_AUTOCOMMIT = None


def check_postgresql_server(database_url: str) -> bool:
    """
    Check if PostgreSQL server is running and accessible
    Returns True if server is accessible, False otherwise
    """
    if not PSYCOPG2_AVAILABLE:
        print("INFO: psycopg2 not available, skipping server check", flush=True)
        logger.info("psycopg2 not available, skipping server check")
        return True

    try:
        # Parse the database URL
        parts = database_url.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_port_db = parts[1].split('/')
        host_port = host_port_db[0].split(':')

        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'

        # Try to connect to postgres database with short timeout
        print(f"Checking PostgreSQL server at {host}:{port}...", flush=True)
        logger.info(f"Checking PostgreSQL server at {host}:{port}...")

        conn = psycopg2.connect(
            dbname='postgres',
            user=username,
            password=password,
            host=host,
            port=port,
            connect_timeout=3  # Short timeout to fail fast
        )
        conn.close()
        print("PostgreSQL server is accessible", flush=True)
        logger.info("PostgreSQL server is running and accessible")
        return True

    except Exception as e:
        error_msg = str(e)
        print(
            f"WARNING: Cannot connect to PostgreSQL: {error_msg}", flush=True)
        logger.error(f"Cannot connect to PostgreSQL server: {e}")
        if 'host' in locals():
            print(
                f"Please ensure PostgreSQL is running at {host}:{port}", flush=True)
            logger.error(
                f"Please ensure PostgreSQL is running at {host}:{port}")
        return False


def create_database_if_not_exists(database_url: str) -> bool:
    """
    Create PostgreSQL database if it doesn't exist
    Returns True if database was created, False if it already existed
    """
    if not PSYCOPG2_AVAILABLE:
        logger.warning(
            "psycopg2 not available, cannot create database automatically")
        logger.info("Please ensure database exists manually")
        return False

    try:
        # Parse the database URL
        # Format: postgresql://user:password@host:port/database
        parts = database_url.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_port_db = parts[1].split('/')
        host_port = host_port_db[0].split(':')

        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        database = host_port_db[1].split('?')[0]  # Remove query params if any

        # Connect to PostgreSQL server (postgres database)
        logger.info(f"Checking if database '{database}' exists...")
        conn = psycopg2.connect(
            dbname='postgres',
            user=username,
            password=password,
            host=host,
            port=port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (database,)
        )
        exists = cursor.fetchone()

        if exists:
            logger.info(f"✅ Database '{database}' already exists")
            cursor.close()
            conn.close()
            return False

        # Create database
        logger.info(f"Creating database '{database}'...")
        cursor.execute(f'CREATE DATABASE "{database}"')
        logger.info(f"✅ Database '{database}' created successfully")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"❌ Database creation error ({error_type}): {e}")
        if 'database' in locals():
            logger.warning(
                f"Could not create database automatically. Please create it manually:")
            logger.warning(f"  CREATE DATABASE {database};")
        return False


def check_alembic_initialized() -> bool:
    """Check if Alembic migrations have been initialized"""
    try:
        alembic_dir = Path(__file__).parent.parent / "alembic"
        versions_dir = alembic_dir / "versions"

        # Check if alembic directory exists
        if not alembic_dir.exists():
            logger.warning("Alembic directory not found")
            return False

        # Check if versions directory exists and has migration files
        if versions_dir.exists():
            migration_files = list(versions_dir.glob("*.py"))
            # Filter out __init__.py
            migration_files = [
                f for f in migration_files if f.name != "__init__.py"]
            if migration_files:
                logger.debug(
                    f"Found {len(migration_files)} Alembic migration files")
                return True

        logger.info("No Alembic migrations found")
        return False
    except Exception as e:
        logger.error(f"Error checking Alembic initialization: {e}")
        return False


def check_migrations_applied(database_url: str) -> bool:
    """Check if Alembic migrations have been applied to the database"""
    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            # Check if alembic_version table exists
            result = connection.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                );
            """))
            exists = result.scalar()

            if exists:
                # Check if there are any applied migrations
                result = connection.execute(text(
                    "SELECT COUNT(*) FROM alembic_version"
                ))
                count = result.scalar()
                if count > 0:
                    logger.debug(f"Found {count} applied Alembic migration(s)")
                    return True

            logger.info("No migrations have been applied yet")
            return False

    except Exception as e:
        logger.debug(f"Could not check migration status: {e}")
        return False


def run_alembic_migrations() -> bool:
    """
    Run Alembic migrations to bring database up to date
    Returns True if successful, False otherwise
    """
    try:
        # Get the backend directory (where alembic.ini is located)
        backend_dir = Path(__file__).parent.parent
        alembic_ini = backend_dir / "alembic.ini"

        if not alembic_ini.exists():
            logger.warning("⚠️  alembic.ini not found - skipping migrations")
            return False

        logger.info("Running Alembic migrations...")

        # Change to backend directory and run alembic upgrade
        original_dir = os.getcwd()
        try:
            os.chdir(backend_dir)

            # First, check if alembic_version table exists and has entries
            # If not, we need to stamp the database with the current revision
            from database.connection import engine
            from sqlalchemy import text

            with engine.connect() as conn:
                # Check if alembic_version table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'alembic_version'
                    );
                """))
                alembic_table_exists = result.scalar()

                if not alembic_table_exists:
                    logger.info(
                        "Alembic version table not found, stamping database...")
                    # Stamp the database with the current revision
                    stamp_result = subprocess.run(
                        ["alembic", "stamp", "head"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if stamp_result.returncode == 0:
                        logger.info("✅ Database stamped successfully")
                    else:
                        logger.warning(
                            f"⚠️  Database stamping failed: {stamp_result.stderr}")
                else:
                    # Check if there are any entries in alembic_version
                    result = conn.execute(
                        text("SELECT COUNT(*) FROM alembic_version"))
                    version_count = result.scalar()
                    if version_count == 0:
                        logger.info(
                            "Alembic version table empty, stamping database...")
                        stamp_result = subprocess.run(
                            ["alembic", "stamp", "head"],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if stamp_result.returncode == 0:
                            logger.info("✅ Database stamped successfully")
                        else:
                            logger.warning(
                                f"⚠️  Database stamping failed: {stamp_result.stderr}")

            # Now run alembic upgrade head
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info("✅ Alembic migrations completed successfully")
                if result.stdout:
                    logger.debug(f"Alembic output: {result.stdout}")
                return True
            else:
                logger.error(
                    f"❌ Alembic migration failed with exit code {result.returncode}")
                if result.stderr:
                    logger.error(f"Error output: {result.stderr}")
                if result.stdout:
                    logger.debug(f"Standard output: {result.stdout}")
                return False

        finally:
            os.chdir(original_dir)

    except FileNotFoundError:
        logger.warning(
            "⚠️  Alembic command not found - please install alembic")
        logger.warning("  pip install alembic")
        return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Alembic migration timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Error running Alembic migrations: {e}")
        return False


def initialize_database(database_url: str) -> bool:
    """
    Complete database initialization:
    1. Check PostgreSQL server is running
    2. Create database if not exists
    3. Run Alembic migrations if available and not applied

    Returns True if successful or already initialized, False on error
    """
    try:
        print("Initializing database...", flush=True)

        # Step 0: Check PostgreSQL server is accessible
        if not check_postgresql_server(database_url):
            print("ERROR: PostgreSQL server is not accessible", flush=True)
            print("Skipping automatic database setup", flush=True)
            logger.error("PostgreSQL server is not accessible")
            logger.info("Please start PostgreSQL and ensure it's running")
            return False

        # Step 1: Create database if it doesn't exist
        print("Checking database exists...", flush=True)
        db_created = create_database_if_not_exists(database_url)
        if db_created:
            print("Database created successfully", flush=True)
            logger.info("Database was created successfully")

        # Step 2: Check and run Alembic migrations
        print("Checking migrations...", flush=True)
        if check_alembic_initialized():
            # Check if migrations have been applied
            if not check_migrations_applied(database_url) or db_created:
                # Run migrations if:
                # - Database was just created, OR
                # - No migrations have been applied yet
                print("Applying database migrations...", flush=True)
                logger.info("Applying database migrations...")
                if run_alembic_migrations():
                    print("Migrations applied successfully", flush=True)
                    logger.info("Database migrations applied successfully")
                else:
                    print("WARNING: Migration failed, continuing anyway...", flush=True)
                    logger.warning(
                        "Migration application failed, but continuing...")
                    logger.warning(
                        "You may need to run 'alembic upgrade head' manually")
            else:
                print("Migrations are up to date", flush=True)
                logger.info("Database migrations are already up to date")
        else:
            print("No migrations configured", flush=True)
            logger.info(
                "No Alembic migrations configured - using direct table creation")

        print("Database initialization complete", flush=True)
        logger.info("Database initialization complete")
        return True

    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        logger.warning("Will attempt to continue with existing database...")
        return False

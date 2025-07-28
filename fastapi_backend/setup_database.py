#!/usr/bin/env python3
"""
Script to set up the database with migrations and initial data
"""

import subprocess
import sys
import os


def run_migration():
    """Run database migrations"""
    try:
        print("🗄️  Setting up database...")

        # Create initial migration
        print("📝 Creating initial migration...")
        result = subprocess.run([
            "alembic", "revision", "--autogenerate", "-m", "Initial migration"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"⚠️  Migration creation warning: {result.stderr}")
        else:
            print("✅ Initial migration created")

        # Apply migrations
        print("🔄 Applying migrations...")
        result = subprocess.run([
            "alembic", "upgrade", "head"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Database migrations applied successfully")
            return True
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False

    except FileNotFoundError:
        print("❌ Alembic not found. Please install it with: pip install alembic")
        return False
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return False


def create_database_schema():
    """Create database schema directly using SQLAlchemy"""
    try:
        print("🗄️  Creating database schema...")

        from database.connection import Base, engine

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database schema created successfully")
        return True

    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up FastAPI Backend Database")
    print("=" * 50)

    # Try migrations first, fallback to direct schema creation
    if not run_migration():
        print("\n🔄 Falling back to direct schema creation...")
        if not create_database_schema():
            print("❌ Database setup failed!")
            sys.exit(1)

    print("\n✅ Database setup complete!")
    print("\n📝 Next steps:")
    print("1. Run: python create_test_users.py")
    print("2. Start server: python main.py")
    print("3. Visit: http://127.0.0.1:8000/docs")


if __name__ == "__main__":
    main()

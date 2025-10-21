#!/usr/bin/env python3
"""
Database Schema Fix Script
Fixes the schema mismatch between existing tables and Alembic migrations
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔍 {description}")
    print(f"   Command: {cmd}")

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"   ✅ Success")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"   ❌ Failed: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Timeout: Command took too long")
        return False
    except Exception as e:
        print(f"   💥 Error: {e}")
        return False


def fix_database_schema():
    """Fix the database schema mismatch"""
    print("=" * 70)
    print("  DATABASE SCHEMA FIX")
    print("=" * 70)
    print()

    # Change to backend directory
    backend_dir = Path(__file__).parent / "fastapi_backend"
    if not backend_dir.exists():
        print("❌ Backend directory not found")
        return False

    original_dir = os.getcwd()
    try:
        os.chdir(backend_dir)
        print(f"📁 Changed to directory: {backend_dir}")

        # Step 1: Check current migration status
        print("\n🔍 Checking current migration status...")
        success, output = run_command(
            "alembic current", "Check current migration")
        if not success:
            print("❌ Could not check migration status")
            return False

        # Step 2: Check if alembic_version table exists
        print("\n🔍 Checking alembic_version table...")
        success, output = run_command(
            "alembic history", "Check migration history")
        if not success:
            print("❌ Could not check migration history")
            return False

        # Step 3: Stamp the database with current revision
        print("\n🔧 Stamping database with current revision...")
        success, output = run_command(
            "alembic stamp head", "Stamp database with head revision")
        if not success:
            print("❌ Could not stamp database")
            return False

        # Step 4: Check if there are any pending migrations
        print("\n🔍 Checking for pending migrations...")
        success, output = run_command(
            "alembic upgrade head", "Apply any pending migrations")
        if not success:
            print("❌ Could not apply migrations")
            return False

        # Step 5: Verify final status
        print("\n🔍 Verifying final migration status...")
        success, output = run_command(
            "alembic current", "Check final migration status")
        if not success:
            print("❌ Could not verify final status")
            return False

        print("\n✅ Database schema fix completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error during schema fix: {e}")
        return False
    finally:
        os.chdir(original_dir)


def main():
    """Main function"""
    print("🚀 Starting Database Schema Fix...")
    print()

    if fix_database_schema():
        print("\n🎉 Database schema fix completed successfully!")
        print("The backend should now start without schema conflicts.")
        return 0
    else:
        print("\n❌ Database schema fix failed.")
        print("You may need to manually reset the database:")
        print("1. Drop and recreate the database")
        print("2. Run migrations from scratch")
        return 1


if __name__ == "__main__":
    sys.exit(main())

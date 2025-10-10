"""
Quick diagnostic script to test if all imports work correctly
Run this before starting the main server to catch import errors
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test all critical imports"""
    errors = []
    
    print("=" * 60)
    print("Testing imports...")
    print("=" * 60)
    
    # Test 1: Core configuration
    try:
        print("[OK] Testing core.config...")
        from core.config import settings
        print(f"  Database URL: {settings.DATABASE_URL[:40]}...")
    except Exception as e:
        errors.append(f"core.config: {e}")
        print(f"[FAIL] core.config failed: {e}")
    
    # Test 2: Database connection
    try:
        print("[OK] Testing database.connection...")
        from database.connection import engine, Base
        print("  SQLAlchemy engine created")
    except Exception as e:
        errors.append(f"database.connection: {e}")
        print(f"[FAIL] database.connection failed: {e}")
    
    # Test 3: Database setup (new module)
    try:
        print("[OK] Testing core.database_setup...")
        from core.database_setup import initialize_database, PSYCOPG2_AVAILABLE
        print(f"  psycopg2 available: {PSYCOPG2_AVAILABLE}")
    except Exception as e:
        errors.append(f"core.database_setup: {e}")
        print(f"[FAIL] core.database_setup failed: {e}")
    
    # Test 4: Security and encryption
    try:
        print("[OK] Testing core.security...")
        from core.security import get_current_user
        print("  Security module loaded")
    except Exception as e:
        errors.append(f"core.security: {e}")
        print(f"[FAIL] core.security failed: {e}")
    
    # Test 5: Encryption service
    try:
        print("[OK] Testing services.encryption_service...")
        from services.encryption_service import encryption_service
        print("  Encryption service loaded")
    except Exception as e:
        errors.append(f"services.encryption_service: {e}")
        print(f"[FAIL] services.encryption_service failed: {e}")
    
    # Test 6: Models
    try:
        print("[OK] Testing models...")
        from models.user import User
        from models.role import Role
        print("  User and Role models loaded")
    except Exception as e:
        errors.append(f"models: {e}")
        print(f"[FAIL] models failed: {e}")
    
    # Test 7: FastAPI app
    try:
        print("[OK] Testing main app...")
        import main
        print("  Main app module loaded")
    except Exception as e:
        errors.append(f"main: {e}")
        print(f"[FAIL] main failed: {e}")
    
    print("=" * 60)
    
    if errors:
        print(f"[ERROR] {len(errors)} import error(s) found:")
        for error in errors:
            print(f"  - {error}")
        print("=" * 60)
        return False
    else:
        print("[SUCCESS] All imports successful!")
        print("=" * 60)
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)

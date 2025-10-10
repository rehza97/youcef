#!/usr/bin/env python3
"""
Deploy KPI Performance Optimizations
Run this script to apply all KPI performance improvements
"""

from sqlalchemy import text
from database.connection import engine
import os
import sys
import subprocess
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from fastapi_backend
sys.path.append(str(Path(__file__).parent.parent))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_sql_file(file_path: str):
    """Execute SQL file using database connection"""
    try:
        with open(file_path, 'r') as f:
            sql_content = f.read()

        # Split by semicolon and execute each statement
        statements = [stmt.strip()
                      for stmt in sql_content.split(';') if stmt.strip()]

        with engine.connect() as conn:
            for statement in statements:
                if statement and not statement.startswith('--'):
                    logger.info(f"Executing: {statement[:50]}...")
                    conn.execute(text(statement))
            conn.commit()

        logger.info(f"✅ Successfully executed {file_path}")

    except Exception as e:
        logger.error(f"❌ Error executing {file_path}: {e}")
        raise


def check_indexes():
    """Check if indexes were created successfully"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname, tablename 
                FROM pg_indexes 
                WHERE tablename = 'parks' 
                AND indexname LIKE 'idx_parks_%'
                ORDER BY indexname;
            """))

            indexes = result.fetchall()
            logger.info(f"📊 Found {len(indexes)} KPI indexes:")
            for idx in indexes:
                logger.info(f"   ✅ {idx[0]} on {idx[1]}")

            return len(indexes) >= 8  # Should have at least 8 indexes

    except Exception as e:
        logger.error(f"❌ Error checking indexes: {e}")
        return False


def test_query_performance():
    """Test query performance with EXPLAIN ANALYZE"""
    try:
        with engine.connect() as conn:
            # Test active subscribers query
            logger.info("🧪 Testing active subscribers query performance...")
            result = conn.execute(text("""
                EXPLAIN (ANALYZE, BUFFERS) 
                SELECT COUNT(*) FROM parks 
                WHERE subscriber_status IN ('Active', 'ACTIVE', 'active');
            """))

            explain_output = result.fetchall()
            for row in explain_output:
                logger.info(f"   {row[0]}")

            # Test DOT-based query
            logger.info("🧪 Testing DOT-based query performance...")
            result = conn.execute(text("""
                EXPLAIN (ANALYZE, BUFFERS) 
                SELECT COUNT(*) FROM parks 
                WHERE dot_id IN (1, 2) AND subscriber_status = 'Active';
            """))

            explain_output = result.fetchall()
            for row in explain_output:
                logger.info(f"   {row[0]}")

    except Exception as e:
        logger.error(f"❌ Error testing query performance: {e}")


def main():
    """Main deployment function"""
    logger.info("🚀 Starting KPI Performance Optimization Deployment...")

    # 1. Create indexes
    logger.info("📊 Step 1: Creating database indexes...")
    sql_file = Path(__file__).parent / "create_kpi_indexes.sql"
    if sql_file.exists():
        run_sql_file(str(sql_file))
    else:
        logger.error(f"❌ SQL file not found: {sql_file}")
        return False

    # 2. Verify indexes
    logger.info("🔍 Step 2: Verifying indexes...")
    if not check_indexes():
        logger.error("❌ Index creation failed or incomplete")
        return False

    # 3. Test performance
    logger.info("⚡ Step 3: Testing query performance...")
    test_query_performance()

    # 4. Restart backend (if running)
    logger.info("🔄 Step 4: Backend restart required...")
    logger.info(
        "   Please restart your FastAPI backend to load the new KPI cache service")

    logger.info("✅ KPI Performance Optimization Deployment Complete!")
    logger.info("")
    logger.info("📈 Expected Performance Improvements:")
    logger.info("   • KPI queries: 10-100× faster (with indexes)")
    logger.info("   • Dashboard load: 10× faster (with caching)")
    logger.info("   • Cache TTL: 5-15 minutes (configurable)")
    logger.info("")
    logger.info("🔧 Next Steps:")
    logger.info("   1. Restart FastAPI backend")
    logger.info("   2. Test dashboard loading speed")
    logger.info("   3. Monitor cache hit rates in logs")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


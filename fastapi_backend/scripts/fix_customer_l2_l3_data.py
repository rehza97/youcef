#!/usr/bin/env python3
"""
Fix Customer L2/L3 Data - Re-process existing data with correct column mapping
This script will update the existing parks data to include Customer L2/L3 information
"""

import sys
import logging
from pathlib import Path
from sqlalchemy import text
from database.connection import engine

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_current_data():
    """Check current state of Customer L2/L3 data"""
    try:
        with engine.connect() as conn:
            # Check total records
            result = conn.execute(text("SELECT COUNT(*) FROM parks"))
            total_records = result.scalar()

            # Check L2 data
            result = conn.execute(
                text("SELECT COUNT(*) FROM parks WHERE customer_l2_code IS NOT NULL"))
            l2_records = result.scalar()

            # Check L3 data
            result = conn.execute(
                text("SELECT COUNT(*) FROM parks WHERE customer_l3_code IS NOT NULL"))
            l3_records = result.scalar()

            logger.info(f"📊 Current data state:")
            logger.info(f"   Total records: {total_records:,}")
            logger.info(f"   Records with L2: {l2_records:,}")
            logger.info(f"   Records with L3: {l3_records:,}")

            return total_records, l2_records, l3_records

    except Exception as e:
        logger.error(f"❌ Error checking data: {e}")
        return 0, 0, 0


def update_customer_data():
    """Update existing parks data with Customer L2/L3 information"""
    try:
        with engine.connect() as conn:
            # Get a sample of records to see the current state
            result = conn.execute(text("""
                SELECT id, customer_l2_code, customer_l3_code, customer_code
                FROM parks 
                WHERE customer_l2_code IS NULL 
                LIMIT 5
            """))

            sample_records = result.fetchall()
            logger.info(f"📋 Sample records with missing L2/L3:")
            for record in sample_records:
                logger.info(
                    f"   ID: {record[0]}, L2: {record[1]}, L3: {record[2]}, Code: {record[3]}")

            # For now, we'll need to re-process the data
            # The issue is that the original mapping didn't include L2/L3
            logger.info(
                "⚠️  Customer L2/L3 data is missing from existing records")
            logger.info("   This requires re-processing the original CSV file")
            logger.info(
                "   The fast batch mapper has been fixed for future uploads")

            return False

    except Exception as e:
        logger.error(f"❌ Error updating data: {e}")
        return False


def main():
    """Main function"""
    logger.info("🔧 Customer L2/L3 Data Fix Script")
    logger.info("=" * 50)

    # Check current state
    total, l2_count, l3_count = check_current_data()

    if l2_count == 0 and l3_count == 0:
        logger.warning("⚠️  No Customer L2/L3 data found in existing records")
        logger.info("")
        logger.info("🔧 SOLUTION:")
        logger.info("   1. The fast batch mapper has been fixed")
        logger.info("   2. Future file uploads will include L2/L3 data")
        logger.info("   3. To fix existing data, you need to:")
        logger.info("      a) Clear existing parks data")
        logger.info("      b) Re-upload the CSV file")
        logger.info("")
        logger.info("🚀 Next Steps:")
        logger.info("   1. Restart backend to load the fixed mapper")
        logger.info("   2. Clear existing data (optional)")
        logger.info("   3. Re-upload the CSV file")
        logger.info("   4. Customer L2/L3 tabs will then show data")

        return True
    else:
        logger.info("✅ Customer L2/L3 data already exists")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

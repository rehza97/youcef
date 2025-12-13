"""
Script to mark existing park records as anomalies based on business rules
This updates records that were processed before the anomaly detection was implemented
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import SessionLocal
from models.park import Park
from models.park_2b import Park2B
from sqlalchemy import or_, and_
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def mark_anomalies_in_table(db, model_class, table_name):
    """Mark anomalies in a given table (parks or parks_2b)"""
    logger.info(f"Processing {table_name} table...")
    
    # Build anomaly conditions
    anomaly_conditions = []
    
    # Rule 1: Customer L3 codes 5 or 57
    anomaly_conditions.append(
        or_(
            model_class.customer_l3_code == '5',
            model_class.customer_l3_code == '57',
            model_class.customer_l3_code == 5,
            model_class.customer_l3_code == 57
        )
    )
    
    # Rule 2: Offer name contains Moohtarif (case-insensitive)
    anomaly_conditions.append(
        model_class.offer_name.ilike('%moohtarif%')
    )
    
    # Rule 3: Offer name contains Solutions Hebergements (case-insensitive)
    anomaly_conditions.append(
        or_(
            model_class.offer_name.ilike('%solutions%hebergements%'),
            model_class.offer_name.ilike('%solutions%hébergements%')
        )
    )
    
    # Rule 4: Telecom Type is X25, WIFI, or WIMAX
    anomaly_conditions.append(
        model_class.telecom_type.in_(['X25', 'WIFI', 'WIMAX'])
    )
    
    # Find records that match anomaly criteria but aren't marked as anomalies
    anomaly_records = db.query(model_class).filter(
        or_(*anomaly_conditions),
        or_(
            model_class.is_anomaly.is_(False),
            model_class.is_anomaly.is_(None)
        )
    ).all()
    
    logger.info(f"Found {len(anomaly_records)} records in {table_name} that need to be marked as anomalies")
    
    # Update each record with appropriate anomaly reason
    updated_count = 0
    for record in anomaly_records:
        reasons = []
        
        # Check each rule and build reason
        if record.customer_l3_code and str(record.customer_l3_code).strip() in ['5', '57']:
            reasons.append(f"Code Customer L3: {record.customer_l3_code}")
        
        if record.offer_name:
            offer_name_lower = str(record.offer_name).lower()
            if 'moohtarif' in offer_name_lower:
                reasons.append("Offer name contains: Moohtarif")
            if 'solutions' in offer_name_lower and ('hebergements' in offer_name_lower or 'hébergements' in offer_name_lower):
                reasons.append("Offer name contains: Solutions Hebergements")
        
        if record.telecom_type and str(record.telecom_type).upper().strip() in ['X25', 'WIFI', 'WIMAX']:
            reasons.append(f"Telecom Type: {record.telecom_type}")
        
        if reasons:
            record.is_anomaly = True
            record.anomaly_reason = "; ".join(reasons)
            updated_count += 1
    
    # Commit all changes
    if updated_count > 0:
        db.commit()
        logger.info(f"✅ Updated {updated_count} records in {table_name} table")
    else:
        logger.info(f"ℹ️  No records to update in {table_name} table")
    
    return updated_count


def main():
    """Main function to mark existing anomalies"""
    db = SessionLocal()
    
    try:
        logger.info("🚀 Starting anomaly marking process...")
        
        # Process parks table
        parks_count = mark_anomalies_in_table(db, Park, "parks")
        
        # Process parks_2b table
        parks_2b_count = mark_anomalies_in_table(db, Park2B, "parks_2b")
        
        total_updated = parks_count + parks_2b_count
        
        logger.info(f"✅ Completed! Total records marked as anomalies: {total_updated}")
        logger.info(f"   - Parks: {parks_count}")
        logger.info(f"   - Parks 2B: {parks_2b_count}")
        
    except Exception as e:
        logger.error(f"❌ Error marking anomalies: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

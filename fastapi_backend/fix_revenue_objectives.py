#!/usr/bin/env python3
"""
Fix existing revenue_journal records to link revenue_objective_id and calculate taux_realisation_ca

UPDATED: Now uses RevenueDOTCorporate (monthly objectives) instead of RevenueObjective
Calculates monthly achievement rates based on date_gl month.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from models.revenue import RevenueJournal, RevenueDOTCorporate
from sqlalchemy import func
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_revenue_objectives():
    """
    Fix revenue_objective_id and taux_realisation_ca for existing records

    Uses RevenueDOTCorporate (monthly objectives) and calculates monthly achievement rates.
    """
    db = SessionLocal()
    try:
        # Get all revenue objectives (from monthly objectives table)
        current_year = datetime.utcnow().year
        objectives = db.query(RevenueDOTCorporate).filter(
            RevenueDOTCorporate.year == current_year
        ).all()
        objective_map = {obj.dot_name.upper().strip(): obj for obj in objectives}

        logger.info(f"📋 Found {len(objectives)} revenue objectives")
        logger.info(f"   Objective names: {list(objective_map.keys())[:10]}...")

        # Get all revenue journal records without objective_id
        records = db.query(RevenueJournal).filter(
            RevenueJournal.revenue_objective_id.is_(None),
            RevenueJournal.org_name.isnot(None)
        ).all()

        logger.info(f"📊 Found {len(records)} revenue records without objective_id")

        updated_count = 0
        skipped_count = 0

        for record in records:
            org_name_normalized = record.org_name.upper().strip()

            # Try exact match first
            objective = objective_map.get(org_name_normalized)

            # If not found, try case-insensitive search with variations
            if not objective:
                for obj_name, obj in objective_map.items():
                    # Handle "BORD BOU ARRERIDJ" vs "BORD-BOU-ARRERIDJ"
                    normalized_record = org_name_normalized.replace('-', ' ').replace('_', ' ')
                    normalized_obj = obj_name.replace('-', ' ').replace('_', ' ')
                    if normalized_record == normalized_obj:
                        objective = obj
                        break

            if objective:
                record.revenue_objective_id = objective.id

                # Calculate monthly achievement rate (CA / Monthly Objective)
                if record.chiffre_aff_exe_dzd and record.date_gl:
                    try:
                        ca = float(record.chiffre_aff_exe_dzd)
                        # Extract month from date_gl
                        month_num = record.date_gl.month if hasattr(record.date_gl, 'month') else None

                        if month_num:
                            # Get month-specific objective
                            monthly_objective = objective.get_month_objective(month_num)
                            if monthly_objective and monthly_objective != 0:
                                record.taux_realisation_ca = (ca / monthly_objective) * 100
                                logger.debug(f"   📊 {record.org_name} Month {month_num}: {ca} / {monthly_objective} = {record.taux_realisation_ca:.2f}%")
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.warning(f"   ⚠️ Error calculating monthly achievement rate: {e}")

                updated_count += 1

                if updated_count % 100 == 0:
                    logger.info(f"   Updated {updated_count} records...")
                    db.flush()
            else:
                skipped_count += 1
                if skipped_count <= 10:
                    logger.warning(f"⚠️ No objective found for org_name: '{record.org_name}'")

        # Commit all changes
        db.commit()

        logger.info(f"✅ Update complete:")
        logger.info(f"   Updated: {updated_count} records")
        logger.info(f"   Skipped: {skipped_count} records (no matching objective)")

        # Verify update
        total_with_objective = db.query(RevenueJournal).filter(
            RevenueJournal.revenue_objective_id.isnot(None)
        ).count()
        logger.info(f"📊 Total records with objective_id: {total_with_objective}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        logger.exception(e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("FIXING REVENUE OBJECTIVES")
    logger.info("=" * 80)
    fix_revenue_objectives()
    logger.info("=" * 80)
    logger.info("DONE")
    logger.info("=" * 80)

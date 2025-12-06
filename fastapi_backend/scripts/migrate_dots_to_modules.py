"""
Data Migration Script: Assign Modules to Existing DOTs

This script helps migrate existing DOTs to the new module-based system.
It provides options to:
1. View current DOT assignments
2. Automatically assign DOTs to modules based on data usage
3. Manually assign specific DOTs to modules
4. Create module-specific duplicates of existing DOTs

Usage:
    python scripts/migrate_dots_to_modules.py --mode [view|auto|manual|duplicate]
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import func
from database.connection import SessionLocal
from models.dot import DOT, MODULE_PARC_CORPORATE_NGBSS, MODULE_CHIFFRE_AFFAIRES, MODULE_ENCAISSEMENT_AR_DOT, MODULE_CREANCE_PERIODIQUE_DOT
from models.park import Park
from models.revenue import RevenueJournal
from models.encaissement import EncaissementARDot
from models.creance import CreancePeriodiqueDot
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def view_current_dots():
    """View all current DOTs and their module assignments"""
    db = SessionLocal()
    try:
        dots = db.query(DOT).order_by(DOT.module, DOT.name).all()

        print("\n" + "=" * 80)
        print("CURRENT DOT STATUS")
        print("=" * 80)

        unassigned = [d for d in dots if d.module is None]
        assigned = [d for d in dots if d.module is not None]

        print(f"\n📊 Summary:")
        print(f"   Total DOTs: {len(dots)}")
        print(f"   Assigned to modules: {len(assigned)}")
        print(f"   Unassigned (no module): {len(unassigned)}")

        if assigned:
            print(f"\n✅ DOTs with module assignments:")
            for dot in assigned:
                print(f"   ID: {dot.id:3d} | Module: {dot.module:30s} | Name: {dot.name}")

        if unassigned:
            print(f"\n⚠️  DOTs without module assignment:")
            for dot in unassigned:
                # Count usage in each table
                park_count = db.query(Park).filter(Park.dot_id == dot.id).count()
                revenue_count = db.query(RevenueJournal).filter(RevenueJournal.dot_id == dot.id).count()
                encaissement_count = db.query(EncaissementARDot).filter(EncaissementARDot.dot_id == dot.id).count()
                creance_count = db.query(CreancePeriodiqueDot).filter(CreancePeriodiqueDot.dot_id == dot.id).count()

                usage = []
                if park_count > 0:
                    usage.append(f"Park:{park_count}")
                if revenue_count > 0:
                    usage.append(f"Revenue:{revenue_count}")
                if encaissement_count > 0:
                    usage.append(f"Encaissement:{encaissement_count}")
                if creance_count > 0:
                    usage.append(f"Créance:{creance_count}")

                usage_str = ", ".join(usage) if usage else "No data"
                print(f"   ID: {dot.id:3d} | Name: {dot.name:20s} | Usage: {usage_str}")

        print("\n" + "=" * 80 + "\n")

    finally:
        db.close()


def auto_assign_modules():
    """Automatically assign modules based on data usage"""
    db = SessionLocal()
    try:
        unassigned_dots = db.query(DOT).filter(DOT.module.is_(None)).all()

        if not unassigned_dots:
            print("✅ All DOTs are already assigned to modules!")
            return

        print(f"\n🤖 Auto-assigning {len(unassigned_dots)} DOTs to modules based on data usage...\n")

        for dot in unassigned_dots:
            # Count usage in each module's tables
            park_count = db.query(Park).filter(Park.dot_id == dot.id).count()
            revenue_count = db.query(RevenueJournal).filter(RevenueJournal.dot_id == dot.id).count()
            encaissement_count = db.query(EncaissementARDot).filter(EncaissementARDot.dot_id == dot.id).count()
            creance_count = db.query(CreancePeriodiqueDot).filter(CreancePeriodiqueDot.dot_id == dot.id).count()

            # Determine which module this DOT belongs to
            usage = {
                MODULE_PARC_CORPORATE_NGBSS: park_count,
                MODULE_CHIFFRE_AFFAIRES: revenue_count,
                MODULE_ENCAISSEMENT_AR_DOT: encaissement_count,
                MODULE_CREANCE_PERIODIQUE_DOT: creance_count
            }

            # Find module with most usage
            max_module = max(usage, key=usage.get)
            max_count = usage[max_module]

            if max_count == 0:
                print(f"⚠️  DOT '{dot.name}' (ID: {dot.id}) has NO data - skipping")
                continue

            # Check if used in multiple modules
            used_in = [m for m, count in usage.items() if count > 0]

            if len(used_in) > 1:
                print(f"⚠️  DOT '{dot.name}' (ID: {dot.id}) is used in MULTIPLE modules:")
                for module in used_in:
                    print(f"      - {module}: {usage[module]} records")
                print(f"      → Assigning to module with most usage: '{max_module}'")

            dot.module = max_module
            print(f"✅ Assigned DOT '{dot.name}' (ID: {dot.id}) to module '{max_module}' ({max_count} records)")

        db.commit()
        print(f"\n✅ Auto-assignment complete!\n")

    except Exception as e:
        db.rollback()
        logger.error(f"Error during auto-assignment: {e}")
        raise
    finally:
        db.close()


def duplicate_dots_for_modules():
    """Create module-specific duplicates of existing DOTs"""
    db = SessionLocal()
    try:
        existing_dots = db.query(DOT).all()

        print(f"\n🔄 Creating module-specific duplicates for {len(existing_dots)} DOTs...\n")

        modules = [
            MODULE_PARC_CORPORATE_NGBSS,
            MODULE_CHIFFRE_AFFAIRES,
            MODULE_ENCAISSEMENT_AR_DOT,
            MODULE_CREANCE_PERIODIQUE_DOT
        ]

        created_count = 0

        for dot in existing_dots:
            for module in modules:
                # Check if DOT already exists for this module
                existing = db.query(DOT).filter(
                    DOT.name == dot.name,
                    DOT.module == module
                ).first()

                if existing:
                    print(f"⏭️  Skipping '{dot.name}' for module '{module}' - already exists")
                    continue

                # Create new DOT for this module
                new_dot = DOT(
                    name=dot.name,
                    module=module,
                    description=f"{dot.description or dot.name} (Module: {module})"
                )
                db.add(new_dot)
                created_count += 1
                print(f"✅ Created '{dot.name}' for module '{module}'")

        db.commit()
        print(f"\n✅ Created {created_count} module-specific DOT duplicates!\n")

    except Exception as e:
        db.rollback()
        logger.error(f"Error during duplication: {e}")
        raise
    finally:
        db.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Migrate DOTs to module-based system')
    parser.add_argument('--mode', choices=['view', 'auto', 'duplicate'], required=True,
                        help='Migration mode: view current status, auto-assign based on usage, or create duplicates')

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("DOT MODULE MIGRATION TOOL")
    print("=" * 80)

    if args.mode == 'view':
        view_current_dots()
    elif args.mode == 'auto':
        print("\n⚠️  WARNING: This will automatically assign modules to unassigned DOTs")
        print("based on their data usage. This action cannot be easily undone.\n")
        confirm = input("Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            auto_assign_modules()
            view_current_dots()
        else:
            print("❌ Cancelled")
    elif args.mode == 'duplicate':
        print("\n⚠️  WARNING: This will create module-specific duplicates of ALL DOTs")
        print("(e.g., 4 'Alger' DOTs - one per module).\n")
        confirm = input("Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            duplicate_dots_for_modules()
            view_current_dots()
        else:
            print("❌ Cancelled")


if __name__ == "__main__":
    main()

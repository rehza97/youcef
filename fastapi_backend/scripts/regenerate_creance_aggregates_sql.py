"""
Script to regenerate Créance Périodique DOT aggregate views using direct SQL
This avoids SQLAlchemy model import issues
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def regenerate_aggregates_sql():
    """Regenerate all Créance aggregate views using SQL"""
    db = SessionLocal()

    try:
        logger.info("Starting aggregate regeneration using SQL...")

        # Step 1: Delete existing aggregates
        logger.info("Deleting existing aggregate views...")
        result = db.execute(text("DELETE FROM creance_aggregate_views"))
        deleted_count = result.rowcount
        db.commit()
        logger.info(f"Deleted {deleted_count} existing aggregate records")

        # Step 2: Generate overview aggregate
        logger.info("Generating overview aggregate...")
        db.execute(text("""
            INSERT INTO creance_aggregate_views
            (view_type, total_invoice_amt, total_invoice_amt_ht, total_open_amt,
             total_tax_amt, total_creance_brut, total_creance_net, total_creance_ht,
             total_avoir_amt, nombre_lignes, created_at, updated_at)
            SELECT
                'overview' as view_type,
                SUM(invoice_amt) as total_invoice_amt,
                SUM(invoice_amt_ht) as total_invoice_amt_ht,
                SUM(open_amt) as total_open_amt,
                SUM(tax_amt) as total_tax_amt,
                SUM(creance_brut) as total_creance_brut,
                SUM(creance_net) as total_creance_net,
                SUM(creance_ht) as total_creance_ht,
                SUM(avoir_amt) as total_avoir_amt,
                COUNT(*) as nombre_lignes,
                NOW() as created_at,
                NOW() as updated_at
            FROM creance_periodique_dot
        """))
        db.commit()
        logger.info("✓ Overview aggregate created")

        # Step 3: Generate by_dot aggregates
        logger.info("Generating by-DOT aggregates...")
        result = db.execute(text("""
            INSERT INTO creance_aggregate_views
            (view_type, dot_id, dot_name, total_invoice_amt, total_invoice_amt_ht,
             total_open_amt, total_tax_amt, total_creance_brut, total_creance_net,
             total_creance_ht, nombre_lignes, created_at, updated_at)
            SELECT
                'by_dot' as view_type,
                dot_id,
                dot,
                SUM(invoice_amt) as total_invoice_amt,
                SUM(invoice_amt_ht) as total_invoice_amt_ht,
                SUM(open_amt) as total_open_amt,
                SUM(tax_amt) as total_tax_amt,
                SUM(creance_brut) as total_creance_brut,
                SUM(creance_net) as total_creance_net,
                SUM(creance_ht) as total_creance_ht,
                COUNT(*) as nombre_lignes,
                NOW() as created_at,
                NOW() as updated_at
            FROM creance_periodique_dot
            WHERE dot IS NOT NULL
            GROUP BY dot_id, dot
            ORDER BY dot
        """))
        by_dot_count = result.rowcount
        db.commit()
        logger.info(f"✓ Generated {by_dot_count} by-DOT aggregates")

        # Step 4: Generate by_annee aggregates
        logger.info("Generating by-year aggregates...")
        result = db.execute(text("""
            INSERT INTO creance_aggregate_views
            (view_type, annee, total_invoice_amt, total_invoice_amt_ht,
             total_open_amt, total_tax_amt, total_creance_brut, total_creance_net,
             total_creance_ht, nombre_lignes, created_at, updated_at)
            SELECT
                'by_annee' as view_type,
                annee,
                SUM(invoice_amt) as total_invoice_amt,
                SUM(invoice_amt_ht) as total_invoice_amt_ht,
                SUM(open_amt) as total_open_amt,
                SUM(tax_amt) as total_tax_amt,
                SUM(creance_brut) as total_creance_brut,
                SUM(creance_net) as total_creance_net,
                SUM(creance_ht) as total_creance_ht,
                COUNT(*) as nombre_lignes,
                NOW() as created_at,
                NOW() as updated_at
            FROM creance_periodique_dot
            WHERE annee IS NOT NULL
            GROUP BY annee
            ORDER BY annee
        """)
        by_annee_count = result.rowcount
        db.commit()
        logger.info(f"✓ Generated {by_annee_count} by-year aggregates")

        # Step 5: Generate by_produit aggregates
        logger.info("Generating by-product aggregates...")
        result = db.execute("""
            INSERT INTO creance_aggregate_views
            (view_type, produit, total_invoice_amt, total_invoice_amt_ht,
             total_open_amt, total_tax_amt, total_creance_brut, total_creance_net,
             total_creance_ht, nombre_lignes, created_at, updated_at)
            SELECT
                'by_produit' as view_type,
                produit,
                SUM(invoice_amt) as total_invoice_amt,
                SUM(invoice_amt_ht) as total_invoice_amt_ht,
                SUM(open_amt) as total_open_amt,
                SUM(tax_amt) as total_tax_amt,
                SUM(creance_brut) as total_creance_brut,
                SUM(creance_net) as total_creance_net,
                SUM(creance_ht) as total_creance_ht,
                COUNT(*) as nombre_lignes,
                NOW() as created_at,
                NOW() as updated_at
            FROM creance_periodique_dot
            WHERE produit IS NOT NULL
            GROUP BY produit
            ORDER BY produit
        """)
        by_produit_count = result.rowcount
        db.commit()
        logger.info(f"✓ Generated {by_produit_count} by-product aggregates")

        # Step 6: Generate by_cust_lev2 aggregates
        logger.info("Generating by-customer-level-2 aggregates...")
        result = db.execute("""
            INSERT INTO creance_aggregate_views
            (view_type, cust_lev2, total_invoice_amt, total_invoice_amt_ht,
             total_open_amt, total_tax_amt, total_creance_brut, total_creance_net,
             total_creance_ht, nombre_lignes, created_at, updated_at)
            SELECT
                'by_cust_lev2' as view_type,
                cust_lev2,
                SUM(invoice_amt) as total_invoice_amt,
                SUM(invoice_amt_ht) as total_invoice_amt_ht,
                SUM(open_amt) as total_open_amt,
                SUM(tax_amt) as total_tax_amt,
                SUM(creance_brut) as total_creance_brut,
                SUM(creance_net) as total_creance_net,
                SUM(creance_ht) as total_creance_ht,
                COUNT(*) as nombre_lignes,
                NOW() as created_at,
                NOW() as updated_at
            FROM creance_periodique_dot
            WHERE cust_lev2 IS NOT NULL
            GROUP BY cust_lev2
            ORDER BY cust_lev2
        """)
        by_cust_lev2_count = result.rowcount
        db.commit()
        logger.info(f"✓ Generated {by_cust_lev2_count} by-customer-level-2 aggregates")

        # Summary
        total_count = 1 + by_dot_count + by_annee_count + by_produit_count + by_cust_lev2_count
        logger.info("\n=== Summary ===")
        logger.info(f"Overview: 1 record")
        logger.info(f"By DOT: {by_dot_count} records")
        logger.info(f"By Year: {by_annee_count} records")
        logger.info(f"By Product: {by_produit_count} records")
        logger.info(f"By Customer Level 2: {by_cust_lev2_count} records")
        logger.info(f"Total: {total_count} records")
        logger.info("✓ Aggregate regeneration complete!")

    except Exception as e:
        logger.error(f"Error regenerating aggregates: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    regenerate_aggregates_sql()

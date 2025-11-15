"""
Script to regenerate Créance Périodique DOT aggregate views
This script deletes existing aggregates and regenerates them from the main table
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func
from database.connection import SessionLocal
from models.creance import CreancePeriodiqueDot, CreanceAggregateView
from models.dot import DOT
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def regenerate_aggregates():
    """Regenerate all Créance aggregate views from the main table"""
    db = SessionLocal()

    try:
        logger.info("Starting aggregate regeneration...")

        # Step 1: Delete existing aggregates
        logger.info("Deleting existing aggregate views...")
        deleted_count = db.query(CreanceAggregateView).delete()
        db.commit()
        logger.info(f"Deleted {deleted_count} existing aggregate records")

        # Step 2: Get DOT mapping for RBAC
        logger.info("Loading DOT mapping...")
        dot_mapping = {}
        dots = db.query(DOT).all()
        for dot in dots:
            dot_mapping[dot.name.upper()] = dot.id
        logger.info(f"Loaded {len(dot_mapping)} DOTs")

        # Step 3: Generate aggregates
        aggregates_to_create = []

        # 3.1: Overview aggregate (global)
        logger.info("Generating overview aggregate...")
        overview_stats = db.query(
            func.sum(CreancePeriodiqueDot.invoice_amt).label('total_invoice_amt'),
            func.sum(CreancePeriodiqueDot.invoice_amt_ht).label('total_invoice_amt_ht'),
            func.sum(CreancePeriodiqueDot.open_amt).label('total_open_amt'),
            func.sum(CreancePeriodiqueDot.tax_amt).label('total_tax_amt'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.creance_ht).label('total_creance_ht'),
            func.sum(CreancePeriodiqueDot.avoir_amt).label('total_avoir_amt'),
            func.count(CreancePeriodiqueDot.id).label('nombre_lignes')
        ).first()

        overview = CreanceAggregateView(
            view_type='overview',
            total_invoice_amt=float(overview_stats.total_invoice_amt or 0),
            total_invoice_amt_ht=float(overview_stats.total_invoice_amt_ht or 0),
            total_open_amt=float(overview_stats.total_open_amt or 0),
            total_tax_amt=float(overview_stats.total_tax_amt or 0),
            total_creance_brut=float(overview_stats.total_creance_brut or 0),
            total_creance_net=float(overview_stats.total_creance_net or 0),
            total_creance_ht=float(overview_stats.total_creance_ht or 0),
            total_avoir_amt=float(overview_stats.total_avoir_amt or 0),
            nombre_lignes=overview_stats.nombre_lignes or 0
        )
        aggregates_to_create.append(overview)
        logger.info(f"Overview aggregate: {overview_stats.nombre_lignes} total records")

        # 3.2: By DOT aggregates
        logger.info("Generating by-DOT aggregates...")
        by_dot_stats = db.query(
            CreancePeriodiqueDot.dot,
            CreancePeriodiqueDot.dot_id,
            func.sum(CreancePeriodiqueDot.invoice_amt).label('total_invoice_amt'),
            func.sum(CreancePeriodiqueDot.invoice_amt_ht).label('total_invoice_amt_ht'),
            func.sum(CreancePeriodiqueDot.open_amt).label('total_open_amt'),
            func.sum(CreancePeriodiqueDot.tax_amt).label('total_tax_amt'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.creance_ht).label('total_creance_ht'),
            func.count(CreancePeriodiqueDot.id).label('nombre_lignes')
        ).filter(CreancePeriodiqueDot.dot.isnot(None)).group_by(
            CreancePeriodiqueDot.dot,
            CreancePeriodiqueDot.dot_id
        ).all()

        for stat in by_dot_stats:
            agg = CreanceAggregateView(
                view_type='by_dot',
                dot_id=stat.dot_id,
                dot_name=stat.dot,
                total_invoice_amt=float(stat.total_invoice_amt or 0),
                total_invoice_amt_ht=float(stat.total_invoice_amt_ht or 0),
                total_open_amt=float(stat.total_open_amt or 0),
                total_tax_amt=float(stat.total_tax_amt or 0),
                total_creance_brut=float(stat.total_creance_brut or 0),
                total_creance_net=float(stat.total_creance_net or 0),
                total_creance_ht=float(stat.total_creance_ht or 0),
                nombre_lignes=stat.nombre_lignes or 0
            )
            aggregates_to_create.append(agg)
        logger.info(f"Generated {len(by_dot_stats)} by-DOT aggregates")

        # 3.3: By ANNEE aggregates
        logger.info("Generating by-year aggregates...")
        by_annee_stats = db.query(
            CreancePeriodiqueDot.annee,
            func.sum(CreancePeriodiqueDot.invoice_amt).label('total_invoice_amt'),
            func.sum(CreancePeriodiqueDot.invoice_amt_ht).label('total_invoice_amt_ht'),
            func.sum(CreancePeriodiqueDot.open_amt).label('total_open_amt'),
            func.sum(CreancePeriodiqueDot.tax_amt).label('total_tax_amt'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.creance_ht).label('total_creance_ht'),
            func.count(CreancePeriodiqueDot.id).label('nombre_lignes')
        ).filter(CreancePeriodiqueDot.annee.isnot(None)).group_by(
            CreancePeriodiqueDot.annee
        ).all()

        for stat in by_annee_stats:
            agg = CreanceAggregateView(
                view_type='by_annee',
                annee=stat.annee,
                total_invoice_amt=float(stat.total_invoice_amt or 0),
                total_invoice_amt_ht=float(stat.total_invoice_amt_ht or 0),
                total_open_amt=float(stat.total_open_amt or 0),
                total_tax_amt=float(stat.total_tax_amt or 0),
                total_creance_brut=float(stat.total_creance_brut or 0),
                total_creance_net=float(stat.total_creance_net or 0),
                total_creance_ht=float(stat.total_creance_ht or 0),
                nombre_lignes=stat.nombre_lignes or 0
            )
            aggregates_to_create.append(agg)
        logger.info(f"Generated {len(by_annee_stats)} by-year aggregates")

        # 3.4: By PRODUIT aggregates
        logger.info("Generating by-product aggregates...")
        by_produit_stats = db.query(
            CreancePeriodiqueDot.produit,
            func.sum(CreancePeriodiqueDot.invoice_amt).label('total_invoice_amt'),
            func.sum(CreancePeriodiqueDot.invoice_amt_ht).label('total_invoice_amt_ht'),
            func.sum(CreancePeriodiqueDot.open_amt).label('total_open_amt'),
            func.sum(CreancePeriodiqueDot.tax_amt).label('total_tax_amt'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.creance_ht).label('total_creance_ht'),
            func.count(CreancePeriodiqueDot.id).label('nombre_lignes')
        ).filter(CreancePeriodiqueDot.produit.isnot(None)).group_by(
            CreancePeriodiqueDot.produit
        ).all()

        for stat in by_produit_stats:
            agg = CreanceAggregateView(
                view_type='by_produit',
                produit=stat.produit,
                total_invoice_amt=float(stat.total_invoice_amt or 0),
                total_invoice_amt_ht=float(stat.total_invoice_amt_ht or 0),
                total_open_amt=float(stat.total_open_amt or 0),
                total_tax_amt=float(stat.total_tax_amt or 0),
                total_creance_brut=float(stat.total_creance_brut or 0),
                total_creance_net=float(stat.total_creance_net or 0),
                total_creance_ht=float(stat.total_creance_ht or 0),
                nombre_lignes=stat.nombre_lignes or 0
            )
            aggregates_to_create.append(agg)
        logger.info(f"Generated {len(by_produit_stats)} by-product aggregates")

        # 3.5: By CUST_LEV2 aggregates
        logger.info("Generating by-customer-level-2 aggregates...")
        by_cust_lev2_stats = db.query(
            CreancePeriodiqueDot.cust_lev2,
            func.sum(CreancePeriodiqueDot.invoice_amt).label('total_invoice_amt'),
            func.sum(CreancePeriodiqueDot.invoice_amt_ht).label('total_invoice_amt_ht'),
            func.sum(CreancePeriodiqueDot.open_amt).label('total_open_amt'),
            func.sum(CreancePeriodiqueDot.tax_amt).label('total_tax_amt'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.creance_ht).label('total_creance_ht'),
            func.count(CreancePeriodiqueDot.id).label('nombre_lignes')
        ).filter(CreancePeriodiqueDot.cust_lev2.isnot(None)).group_by(
            CreancePeriodiqueDot.cust_lev2
        ).all()

        for stat in by_cust_lev2_stats:
            agg = CreanceAggregateView(
                view_type='by_cust_lev2',
                cust_lev2=stat.cust_lev2,
                total_invoice_amt=float(stat.total_invoice_amt or 0),
                total_invoice_amt_ht=float(stat.total_invoice_amt_ht or 0),
                total_open_amt=float(stat.total_open_amt or 0),
                total_tax_amt=float(stat.total_tax_amt or 0),
                total_creance_brut=float(stat.total_creance_brut or 0),
                total_creance_net=float(stat.total_creance_net or 0),
                total_creance_ht=float(stat.total_creance_ht or 0),
                nombre_lignes=stat.nombre_lignes or 0
            )
            aggregates_to_create.append(agg)
        logger.info(f"Generated {len(by_cust_lev2_stats)} by-customer-level-2 aggregates")

        # Step 4: Save all aggregates
        logger.info(f"Saving {len(aggregates_to_create)} aggregate records...")
        db.bulk_save_objects(aggregates_to_create)
        db.commit()

        logger.info("✓ Aggregate regeneration complete!")
        logger.info(f"Total aggregates created: {len(aggregates_to_create)}")

        # Summary
        logger.info("\n=== Summary ===")
        logger.info(f"Overview: 1 record")
        logger.info(f"By DOT: {len(by_dot_stats)} records")
        logger.info(f"By Year: {len(by_annee_stats)} records")
        logger.info(f"By Product: {len(by_produit_stats)} records")
        logger.info(f"By Customer Level 2: {len(by_cust_lev2_stats)} records")
        logger.info(f"Total: {len(aggregates_to_create)} records")

    except Exception as e:
        logger.error(f"Error regenerating aggregates: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    regenerate_aggregates()

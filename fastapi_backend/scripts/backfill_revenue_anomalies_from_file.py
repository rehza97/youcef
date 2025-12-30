#!/usr/bin/env python3
"""
Backfill RevenueAnomaly.original_data with FULL journal row columns.

Why:
- Older anomaly rows were stored with only a few fields (and sometimes as str(dict)),
  so anomaly exports cannot include full journal columns with data.
- FileUpload.file_path still points to the original uploaded file, so we can re-read it,
  re-detect anomalies, and re-save anomalies with full row data.

Usage:
  python fastapi_backend/scripts/backfill_revenue_anomalies_from_file.py --file-upload-id 28
"""

import argparse
import logging
import os
import sys

# Ensure imports work when running as a script
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database.connection import SessionLocal
from models.file_upload import FileUpload
from models.revenue import RevenueAnomaly
from services.revenue_processing import RevenueDataProcessor

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file-upload-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        upload = db.query(FileUpload).filter(FileUpload.id == args.file_upload_id).first()
        if not upload:
            raise SystemExit(f"FileUpload {args.file_upload_id} not found")

        file_path = upload.file_path
        logger.info(f"📄 Backfilling revenue anomalies from file_upload_id={upload.id}")
        logger.info(f"📄 File path: {file_path}")

        processor = RevenueDataProcessor(db)

        # Read and run rules up to anomaly detection (same pipeline)
        df = processor._read_file(file_path)  # noqa: SLF001 (internal usage for backfill)
        processor._apply_journal_processing_rules(df, progress_callback=None)  # noqa: SLF001

        # Build anomalies_data from processor.anomalies (now includes full_row_data)
        anomalies_data = []
        from datetime import datetime

        for anomaly in processor.anomalies:
            row_data = anomaly.get("full_row_data", {}) or {}
            record = dict(row_data)
            record["Type Anomalie"] = anomaly.get("type", "Chiffre d'Affaires AR DOT")
            record["Raison Anomalie"] = anomaly.get("reason", "")
            record["Date Detection"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Ensure key fields exist
            record.setdefault("Org Name", anomaly.get("org_name", ""))
            record.setdefault("N Fact", anomaly.get("n_fact", ""))
            record.setdefault("Cpt Comptable", anomaly.get("cpt_comptable", ""))
            record.setdefault("Description (ligne de produit)", anomaly.get("description", ""))

            anomalies_data.append(record)

        logger.info(f"🚩 Detected anomalies: {len(anomalies_data)}")

        existing_count = db.query(RevenueAnomaly).filter(
            RevenueAnomaly.file_upload_id == upload.id
        ).count()
        logger.info(f"🗑️ Existing anomalies for this file_upload: {existing_count}")

        if args.dry_run:
            logger.info("✅ Dry-run: no database changes were made.")
            return 0

        # Replace anomalies for this file_upload_id
        db.query(RevenueAnomaly).filter(
            RevenueAnomaly.file_upload_id == upload.id
        ).delete(synchronize_session=False)

        if anomalies_data:
            processor._save_anomalies_to_database(anomalies_data, upload.id)  # noqa: SLF001

        db.commit()
        logger.info("✅ Backfill completed and committed.")
        return 0

    except Exception as e:
        db.rollback()
        logger.exception(f"❌ Backfill failed: {e}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())










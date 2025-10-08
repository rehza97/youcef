#!/usr/bin/env python3
"""
Analyze Null Columns in Database
Identifies which CSV columns are not being mapped correctly
"""

import logging
from sqlalchemy import text
from database.connection import get_db
from services.fast_batch_mapper import fast_mapper
import pandas as pd
import sys
import os
sys.path.append('.')


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_null_columns():
    """Analyze which columns have null values and why"""

    print("🔍 ANALYZING NULL COLUMNS IN DATABASE")
    print("=" * 50)

    # 1. Load CSV sample to see all available columns
    csv_path = 'uploads/csv/8cd96816-2ab0-4850-b76b-c6d086ac7c9d.csv'
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return

    df_csv = pd.read_csv(csv_path, nrows=5)
    print(f"📄 CSV has {len(df_csv.columns)} columns")

    # 2. Check database for null columns
    db = next(get_db())

    # Get null counts for each column
    null_queries = [
        ("customer_l1_code",
         "SELECT COUNT(*) as null_count FROM parks WHERE customer_l1_code IS NULL"),
        ("customer_l1_description",
         "SELECT COUNT(*) as null_count FROM parks WHERE customer_l1_description IS NULL"),
        ("customer_l2_code",
         "SELECT COUNT(*) as null_count FROM parks WHERE customer_l2_code IS NULL"),
        ("customer_l2_description",
         "SELECT COUNT(*) as null_count FROM parks WHERE customer_l2_description IS NULL"),
        ("customer_l3_code",
         "SELECT COUNT(*) as null_count FROM parks WHERE customer_l3_code IS NULL"),
        ("customer_l3_description",
         "SELECT COUNT(*) as null_count FROM parks WHERE customer_l3_description IS NULL"),
        ("rental_fees", "SELECT COUNT(*) as null_count FROM parks WHERE rental_fees IS NULL"),
        ("expiry_date", "SELECT COUNT(*) as null_count FROM parks WHERE expiry_date IS NULL"),
        ("iccid", "SELECT COUNT(*) as null_count FROM parks WHERE iccid IS NULL"),
        ("imsi", "SELECT COUNT(*) as null_count FROM parks WHERE imsi IS NULL"),
        ("contact_number", "SELECT COUNT(*) as null_count FROM parks WHERE contact_number IS NULL"),
        ("updated_at", "SELECT COUNT(*) as null_count FROM parks WHERE updated_at IS NULL"),
    ]

    print("\n📊 NULL COLUMN ANALYSIS:")
    print("-" * 40)

    total_records = None
    for col_name, query in null_queries:
        try:
            result = db.execute(text(query)).fetchone()
            null_count = result[0] if result else 0

            if total_records is None:
                # Get total records count
                total_result = db.execute(
                    text("SELECT COUNT(*) FROM parks")).fetchone()
                total_records = total_result[0] if total_result else 0

            percentage = (null_count / total_records *
                          100) if total_records > 0 else 0
            status = "❌ ALL NULL" if null_count == total_records else f"⚠️  {percentage:.1f}% NULL" if percentage > 50 else "✅ OK"

            print(f"{col_name:25} | {null_count:8,} / {total_records:8,} | {status}")

        except Exception as e:
            print(f"{col_name:25} | ERROR: {e}")

    # 3. Test column mapping
    print(f"\n🔍 TESTING COLUMN MAPPING:")
    print("-" * 40)

    # Test each problematic column
    test_columns = [
        ("customer_l1_code", ["code customer l1", "customer l1"]),
        ("customer_l1_description", [
         "description customer l1", "customer l1 description"]),
        ("customer_l2_code", ["code customer l2", "customer l2"]),
        ("customer_l2_description", [
         "description customer l2", "customer l2 description"]),
        ("customer_l3_code", ["code customer l3", "customer l3"]),
        ("customer_l3_description", [
         "description customer l3", "customer l3 description"]),
        ("rental_fees", ["rental fees", "abonnement"]),
        ("expiry_date", ["expiry date", "expiration"]),
        ("iccid", ["iccid", "sim"]),
        ("imsi", ["imsi"]),
        ("contact_number", ["contact number", "numéro de contact"]),
    ]

    for db_col, keywords in test_columns:
        found_col = fast_mapper._find_column(df_csv, keywords)
        if found_col:
            sample_data = df_csv[found_col].iloc[0] if len(
                df_csv) > 0 else "N/A"
            print(f"✅ {db_col:25} -> '{found_col}' (sample: {sample_data})")
        else:
            print(f"❌ {db_col:25} -> NOT FOUND (keywords: {keywords})")

    # 4. Show sample data for problematic columns
    print(f"\n📋 SAMPLE DATA FROM CSV:")
    print("-" * 40)

    sample_cols = [
        "Code Customer L1_Code Catégorie level 1",
        "Description Customer L1_Nom du Catégorie level 1",
        "Code Customer L2_Code Catégorie level 2",
        "Description Customer L2_Nom du Catégorie level 2",
        "Code Customer L3_Code Catégorie level 3",
        "Description Customer L3_Nom du Catégorie level 3",
        "Rental Fees_Frais d'abonnement",
        "Expiry Date_Date d'expiration",
        "ICCID_N° SIM",
        "IMSI_IMSI",
        "Contact number_Numéro de contact"
    ]

    for col in sample_cols:
        if col in df_csv.columns:
            sample = df_csv[col].iloc[0] if len(df_csv) > 0 else "N/A"
            print(f"{col:40} | {sample}")
        else:
            print(f"{col:40} | NOT FOUND")

    db.close()
    print(f"\n✅ Analysis complete!")


if __name__ == "__main__":
    analyze_null_columns()

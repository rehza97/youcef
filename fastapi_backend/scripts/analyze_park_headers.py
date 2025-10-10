#!/usr/bin/env python3
"""
Analyze Park Headers - Compare CSV columns with database mapping
"""

import pandas as pd
import os


def analyze_headers():
    """Analyze the park CSV headers"""

    # Expected columns from the image
    expected_columns = [
        "Extraction DOT",
        "Actel Code",
        "Code Cust",
        "Description Code",
        "Custo Description",
        "Code Custo Description",
        "Telecom ty",
        "Offer Ty",
        "pe",
        "Offer name",
        "Rental Fee",
        "Customer cSer",
        "vice nur",
        "Related Se",
        "USERNAME",
        "Subscriber",
        "Status date",
        "Creation Ds",
        "Active Date",
        "CSR N",
        "ame",
        "Departmen",
        "State",
        "Wila Area",
        "Daira T",
        "own",
        "Com Grid",
        "Quart Street",
        "Voi Street N",
        "um",
        "Building Nc",
        "Unit",
        "Escali Floor",
        "Etage Ho",
        "use No.",
        "Additional",
        "Customer 1",
        "Province",
        "V District",
        "DaiCity",
        "Commr",
        "Postal Code",
        "Expl",
        "ry Date",
        "ICCID_N°",
        "SI IMSI",
        "IMSI",
        "Contact nur"
    ]

    print("📋 Expected columns from image:")
    for i, col in enumerate(expected_columns, 1):
        print(f"  {i:2d}. {col}")

    # Check actual CSV file
    csv_path = 'uploads/csv/8cd96816-2ab0-4850-b76b-c6d086ac7c9d.csv'
    if os.path.exists(csv_path):
        print(f"\n📁 Actual CSV columns from {csv_path}:")
        df = pd.read_csv(csv_path, nrows=1)

        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")

        print(f"\n📊 Total columns: {len(df.columns)}")

        # Check for customer-related columns
        customer_cols = [col for col in df.columns if 'customer' in col.lower(
        ) or 'l1' in col.lower() or 'l2' in col.lower() or 'l3' in col.lower()]
        print(f"\n🔍 Customer-related columns found:")
        for col in customer_cols:
            print(f"  - {col}")

        # Check sample data
        if customer_cols:
            print(f"\n📋 Sample data from first row:")
            for col in customer_cols:
                value = df[col].iloc[0]
                print(f"  {col}: {value}")
    else:
        print(f"\n❌ CSV file not found: {csv_path}")


if __name__ == "__main__":
    analyze_headers()


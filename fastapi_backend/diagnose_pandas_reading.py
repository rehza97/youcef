#!/usr/bin/env python3
"""
Diagnose how pandas reads the revenue file and what dtypes it assigns
"""

import pandas as pd
import sys

# Find the revenue file
revenue_file = "fastapi_backend/uploads/AT- Journal Chiffre d affaire.xls"

print("=" * 80)
print("DIAGNOSING PANDAS FILE READING BEHAVIOR")
print("=" * 80)
print()

try:
    # Read the file the same way the ETL does
    print(f"Reading file: {revenue_file}")
    print()

    # Try reading as HTML (which the ETL likely does for .xls files)
    html_tables = pd.read_html(revenue_file, header=None)
    print(f"✓ Found {len(html_tables)} HTML table(s)")

    # Get the largest table (most columns)
    best_table = max(html_tables, key=lambda t: len(t.columns))
    print(f"✓ Using table with {len(best_table.columns)} columns, {len(best_table)} rows")
    print()

    # Find header row (look for "Chiffre Aff Exe Dzd")
    header_row = None
    for idx in range(min(20, len(best_table))):
        row_values = [str(val).lower() for val in best_table.iloc[idx].values]
        if any('chiffre' in val and 'dzd' in val for val in row_values):
            header_row = idx
            break

    if header_row is None:
        print("❌ Could not find header row!")
        sys.exit(1)

    print(f"✓ Found header row at index: {header_row}")

    # Extract headers and data
    headers = best_table.iloc[header_row].astype(str).tolist()
    df = best_table.iloc[header_row + 1:].copy()
    df.columns = headers
    df.reset_index(drop=True, inplace=True)

    print(f"✓ Created DataFrame with {len(df)} rows")
    print()

    # Find the "Chiffre Aff Exe Dzd" column
    chiffre_col = None
    for col in df.columns:
        if 'chiffre' in str(col).lower() and 'dzd' in str(col).lower():
            chiffre_col = col
            break

    if chiffre_col is None:
        print("❌ Could not find 'Chiffre Aff Exe Dzd' column!")
        sys.exit(1)

    print(f"✓ Found column: '{chiffre_col}'")
    print()

    # Analyze the column
    print("COLUMN ANALYSIS:")
    print("-" * 80)
    print(f"Column name: '{chiffre_col}'")
    print(f"Data type: {df[chiffre_col].dtype}")
    print(f"Non-null values: {df[chiffre_col].notna().sum()}/{len(df)}")
    print()

    # Show first 20 values with their types
    print("First 20 values:")
    print("-" * 80)
    for idx in range(min(20, len(df))):
        value = df[chiffre_col].iloc[idx]
        value_type = type(value).__name__
        value_str = str(value)
        print(f"  Row {idx+1:3d}: {value_str:20s} (type: {value_type})")

    print()
    print("CRITICAL FINDINGS:")
    print("-" * 80)

    # Check if values are floats or strings
    first_20 = df[chiffre_col].head(20)
    float_count = sum(1 for v in first_20 if isinstance(v, (int, float)) and pd.notna(v))
    str_count = sum(1 for v in first_20 if isinstance(v, str))

    print(f"Float values: {float_count}/20")
    print(f"String values: {str_count}/20")
    print()

    if float_count > str_count:
        print("⚠️  PANDAS CONVERTED VALUES TO FLOATS!")
        print("    This means commas were treated as thousands separators.")
        print("    Example: '4320000,00' → 43200000.0 (10x error)")
        print()
        print("    Solution: Force dtype=str when reading HTML tables")
    else:
        print("✓  Values are preserved as strings - parsing should work correctly")

except FileNotFoundError:
    print(f"❌ File not found: {revenue_file}")
    print("   Please provide the correct path to the revenue file")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

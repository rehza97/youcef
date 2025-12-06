#!/usr/bin/env python3
"""
Analysis script to log and understand how revenue fields are processed:
- 'Chiffre Aff Exe Dzd' (numeric field)
- 'N Client' (customer number - stored as string)
- 'Client' (customer name - string)
"""

import sys
sys.path.insert(0, 'fastapi_backend')

from revenue_column_mapping import (
    smart_parse_numeric, 
    safe_float, 
    safe_string,
    map_revenue_journal_record
)

def analyze_field_treatment():
    """Analyze how different fields are treated"""
    
    print("="*80)
    print("REVENUE FIELDS TREATMENT ANALYSIS")
    print("="*80)
    print()
    
    # Sample test data based on user's image
    test_records = [
        {
            "Org Name": "TEST DOT",
            "N Client": "229447",
            "Client": "APC TIMMI",
            "Chiffre Aff Exe Dzd": "4.320.000,00"
        },
        {
            "Org Name": "TEST DOT",
            "N Client": "381425",
            "Client": "SONATRACH DIVISION PRODUCTION",
            "Chiffre Aff Exe Dzd": "1.200.000,00"
        },
        {
            "Org Name": "TEST DOT",
            "N Client": "650518",
            "Client": "DIRECTION DES DOMAINES",
            "Chiffre Aff Exe Dzd": "864.000,00"
        },
        {
            "Org Name": "TEST DOT",
            "N Client": "44162",
            "Client": "ETABLISSEMENT DE REEDUCATION ADRAR",
            "Chiffre Aff Exe Dzd": "203.981,52"
        },
    ]
    
    print("1. FIELD: 'Chiffre Aff Exe Dzd' (NUMERIC)")
    print("-" * 80)
    print("Processing: Uses smart_parse_numeric() → safe_float()")
    print("Database Type: NUMERIC(15, 2)")
    print()
    print("Sample transformations:")
    
    ca_values = [
        "4.320.000,00",
        "1.200.000,00",
        "864.000,00",
        "203.981,52",
        "4.320.000.00",  # Mixed format
        "1.200.000.00",  # Mixed format
        "-662.732,01",
        "67.993,80"
    ]
    
    for val in ca_values:
        parsed = smart_parse_numeric(val)
        print(f"  '{val:20}' → {parsed:>15.2f} (type: {type(parsed).__name__})")
    
    print()
    print("="*80)
    print()
    
    print("2. FIELD: 'N Client' (CUSTOMER NUMBER)")
    print("-" * 80)
    print("Processing: Uses safe_string()")
    print("Database Type: String(100) - STORED AS STRING, NOT NUMBER!")
    print()
    print("⚠️  IMPORTANT: Even though N Client contains numbers, it's stored as STRING")
    print("   This allows preserving leading zeros and handling non-numeric values")
    print()
    print("Sample transformations:")
    
    n_client_values = [
        "229447",
        "381425",
        "650518",
        "44162",
        "0650518",  # With leading zero
        "123.456",  # With dots (should stay as string)
    ]
    
    for val in n_client_values:
        processed = safe_string(val)
        print(f"  Input: '{val:15}' → Output: '{processed}' (type: {type(processed).__name__})")
        print(f"           Database: Stored as String(100), NOT converted to integer")
    
    print()
    print("="*80)
    print()
    
    print("3. FIELD: 'Client' (CUSTOMER NAME)")
    print("-" * 80)
    print("Processing: Uses safe_string()")
    print("Database Type: String(255)")
    print()
    print("Sample transformations:")
    
    client_names = [
        "APC TIMMI",
        "SONATRACH DIVISION PRODUCTION",
        "DIRECTION DES DOMAINES",
        "ETABLISSEMENT DE REEDUCATION ADRAR",
        "SERVICES EXTERNE ( JUSTICE)",
        "DIRECTION DES CADASTRES ET DE LA CONSERVATION FONCIERE",
    ]
    
    for val in client_names:
        processed = safe_string(val)
        print(f"  Input: '{val:60}'")
        print(f"  Output: '{processed}' (type: {type(processed).__name__})")
    
    print()
    print("="*80)
    print()
    
    print("4. COMPLETE RECORD PROCESSING")
    print("-" * 80)
    print("Full mapping example:")
    print()
    
    sample_record = {
        "Org Name": "TEST DOT",
        "N Client": "229447",
        "Client": "APC TIMMI",
        "Chiffre Aff Exe Dzd": "4.320.000,00"
    }
    
    mapped = map_revenue_journal_record(sample_record)
    
    print(f"Original Record:")
    for key, value in sample_record.items():
        print(f"  {key:25} = {value}")
    
    print()
    print(f"Mapped to Database:")
    print(f"  org_name                 = '{mapped.get('org_name')}'")
    print(f"  n_client                 = '{mapped.get('n_client')}' (String in DB)")
    print(f"  client                   = '{mapped.get('client')}' (String in DB)")
    print(f"  chiffre_aff_exe_dzd      = {mapped.get('chiffre_aff_exe_dzd')} (Numeric in DB)")
    print()
    print("="*80)
    print()
    
    print("5. KEY DIFFERENCES")
    print("-" * 80)
    print()
    print("N Client vs Client:")
    print("  • N Client: Contains numeric IDs but stored as STRING")
    print("    - Allows preserving format (leading zeros, etc.)")
    print("    - Can handle non-numeric codes if needed")
    print("    - Database: String(100)")
    print()
    print("  • Client: Contains text names, stored as STRING")
    print("    - Full customer name")
    print("    - Database: String(255)")
    print()
    print("Chiffre Aff Exe Dzd:")
    print("  • Contains monetary amounts, stored as NUMERIC")
    print("    - Smart parsing handles multiple formats")
    print("    - Database: NUMERIC(15, 2)")
    print("    - Can perform calculations on this field")
    print()
    
    print("="*80)
    print()
    print("SUMMARY:")
    print("  1. 'Chiffre Aff Exe Dzd' → NUMERIC (smart parsed, can do math)")
    print("  2. 'N Client' → STRING (preserves format, not a number)")
    print("  3. 'Client' → STRING (text name)")
    print()
    print("="*80)

if __name__ == "__main__":
    analyze_field_treatment()



#!/usr/bin/env python3
"""
Script to log all values from revenue_journal table:
- All 'Chiffre Aff Exe Dzd' values
- All 'N Client' values  
- All 'Client' values

This helps verify how data is being stored in the database.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fastapi_backend'))

def log_all_revenue_values():
    """Log all values from revenue_journal table"""
    
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from database.connection import Base, get_db_url
        from models.revenue import RevenueJournal
        import logging
        
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Create database connection
        db_url = get_db_url()
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            # Get all revenue journal records
            logger.info("Fetching all revenue journal records...")
            records = db.query(RevenueJournal).all()
            
            print("="*80)
            print(f"REVENUE JOURNAL VALUES LOG")
            print("="*80)
            print(f"Total records: {len(records)}")
            print()
            
            # Collect unique values for analysis
            chiffre_aff_values = []
            n_client_values = []
            client_values = []
            
            print("="*80)
            print("1. CHIFFRE AFF EXE DZD VALUES")
            print("="*80)
            print()
            
            for i, record in enumerate(records, 1):
                ca_value = record.chiffre_aff_exe_dzd
                if ca_value is not None:
                    chiffre_aff_values.append(float(ca_value))
                    print(f"{i:6} | ID: {record.id:6} | Chiffre Aff Exe Dzd: {float(ca_value):>15,.2f}")
            
            print()
            print(f"Total non-null values: {len(chiffre_aff_values)}")
            if chiffre_aff_values:
                print(f"Sum: {sum(chiffre_aff_values):,.2f}")
                print(f"Min: {min(chiffre_aff_values):,.2f}")
                print(f"Max: {max(chiffre_aff_values):,.2f}")
                print(f"Average: {sum(chiffre_aff_values)/len(chiffre_aff_values):,.2f}")
            
            print()
            print("="*80)
            print("2. N CLIENT VALUES (STORED AS STRING)")
            print("="*80)
            print()
            print("Note: N Client is stored as String(100), not as a number!")
            print()
            
            unique_n_clients = {}
            
            for i, record in enumerate(records, 1):
                n_client = record.n_client
                if n_client:
                    n_client_str = str(n_client)
                    n_client_values.append(n_client_str)
                    
                    if n_client_str not in unique_n_clients:
                        unique_n_clients[n_client_str] = []
                    unique_n_clients[n_client_str].append(record.id)
            
            # Show unique N Client values
            print(f"Unique N Client values: {len(unique_n_clients)}")
            print()
            print("First 50 N Client values:")
            for i, (n_client, ids) in enumerate(list(unique_n_clients.items())[:50], 1):
                count = len(ids)
                print(f"{i:3} | N Client: '{n_client:15}' | Type: {type(n_client).__name__} | Appears {count:3} times")
            
            print()
            print("="*80)
            print("3. CLIENT VALUES (STORED AS STRING)")
            print("="*80)
            print()
            
            unique_clients = {}
            
            for i, record in enumerate(records, 1):
                client = record.client
                if client:
                    client_str = str(client)
                    client_values.append(client_str)
                    
                    if client_str not in unique_clients:
                        unique_clients[client_str] = []
                    unique_clients[client_str].append(record.id)
            
            # Show unique Client values
            print(f"Unique Client names: {len(unique_clients)}")
            print()
            print("First 50 Client names:")
            for i, (client, ids) in enumerate(list(unique_clients.items())[:50], 1):
                count = len(ids)
                client_display = client[:60] + "..." if len(client) > 60 else client
                print(f"{i:3} | Client: '{client_display:60}' | Type: {type(client).__name__} | Appears {count:3} times")
            
            print()
            print("="*80)
            print("4. SAMPLE RECORDS WITH ALL THREE FIELDS")
            print("="*80)
            print()
            
            # Show sample records
            sample_count = min(20, len(records))
            print(f"Showing first {sample_count} records:")
            print()
            print(f"{'ID':>6} | {'N Client':>15} | {'Chiffre Aff Exe Dzd':>20} | {'Client':<50}")
            print("-" * 100)
            
            for record in records[:sample_count]:
                n_client = str(record.n_client) if record.n_client else "NULL"
                ca_value = f"{float(record.chiffre_aff_exe_dzd):>20,.2f}" if record.chiffre_aff_exe_dzd else "NULL"
                client = str(record.client)[:50] if record.client else "NULL"
                
                print(f"{record.id:>6} | {n_client:>15} | {ca_value:>20} | {client:<50}")
            
            print()
            print("="*80)
            print("5. TYPE ANALYSIS")
            print("="*80)
            print()
            
            # Check types of sample values
            if records:
                sample = records[0]
                print(f"Sample Record ID: {sample.id}")
                print()
                
                ca_type = type(sample.chiffre_aff_exe_dzd).__name__ if sample.chiffre_aff_exe_dzd else "None"
                n_client_type = type(sample.n_client).__name__ if sample.n_client else "None"
                client_type = type(sample.client).__name__ if sample.client else "None"
                
                print(f"chiffre_aff_exe_dzd:")
                print(f"  Value: {sample.chiffre_aff_exe_dzd}")
                print(f"  Python Type: {ca_type}")
                print(f"  Database Type: NUMERIC(15, 2)")
                print()
                
                print(f"n_client:")
                print(f"  Value: '{sample.n_client}'")
                print(f"  Python Type: {n_client_type}")
                print(f"  Database Type: String(100) ⚠️  STORED AS STRING!")
                print()
                
                print(f"client:")
                print(f"  Value: '{sample.client}'")
                print(f"  Python Type: {client_type}")
                print(f"  Database Type: String(255)")
                print()
            
            print("="*80)
            print()
            print("SUMMARY:")
            print(f"  • Total records: {len(records)}")
            print(f"  • Records with Chiffre Aff Exe Dzd: {len(chiffre_aff_values)}")
            print(f"  • Unique N Client values: {len(unique_n_clients)}")
            print(f"  • Unique Client names: {len(unique_clients)}")
            print()
            print("KEY FINDINGS:")
            print("  ✅ Chiffre Aff Exe Dzd is stored as NUMERIC (can do calculations)")
            print("  ⚠️  N Client is stored as STRING (even though it's a number)")
            print("  ✅ Client is stored as STRING (customer name)")
            print()
            print("="*80)
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    log_all_revenue_values()






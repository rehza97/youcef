"""
Revenue (Chiffre d'Affaires AR DOT) Processing Service
Handles data filtering, transformation, and validation for revenue files
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import logging
from sqlalchemy.orm import Session
from models.revenue import RevenueJournal, AccountDescription, RevenueObjective, RevenueAnomaly, RevenueDOTCorporate
from models.dot import DOT
from services.dot_service import DOTService
import re

logger = logging.getLogger(__name__)


class RevenueDataProcessor:
    """Processes Revenue data according to Chiffre d'Affaires AR DOT rules"""

    def __init__(self, db: Session):
        self.db = db
        self.anomalies = []
        self.processed_count = 0
        self.filtered_count = 0
        self.account_descriptions = {}  # Cache for account descriptions
        self.revenue_objectives = {}  # Cache for revenue objectives

    def _get_or_create_dot(self, name: str, description: str = None) -> DOT:
        """Get or create a DOT for Chiffre d'Affaires module
        
        Args:
            name: DOT name (will be normalized)
            description: Optional description for the DOT
            
        Returns:
            DOT object with module-specific assignment
        """
        from models.dot import MODULE_CHIFFRE_AFFAIRES

        # Use DOTService to create module-specific DOT
        # DOTService already logs when creating new DOTs, so we don't need to log here
        dot = DOTService.get_or_create_dot(
            db=self.db,
            name=name,
            description=description,
            module=MODULE_CHIFFRE_AFFAIRES
        )
        return dot

    def process_revenue_journal(self, file_path: str, file_upload_id: int = None,
                                 progress_callback=None) -> Dict[str, Any]:
        """
        Process Revenue Journal file (AT- Journal Chiffre d affaire)

        Args:
            file_path: Path to the file (CSV or Excel)
            file_upload_id: ID of the file upload record
            progress_callback: Callback function for progress updates

        Returns:
            Dict containing processing results and statistics
        """
        try:
            # Read file
            df = self._read_file(file_path)
            logger.info(f"Loaded {len(df)} rows from revenue journal file")

            # Apply processing rules
            df_processed = self._apply_journal_processing_rules(
                df, progress_callback)

            # Generate statistics
            stats = self._generate_statistics(df_processed)

            # Save to database
            processed_data = df_processed.to_dict('records')
            
            save_result = self._save_journal_to_database(
                processed_data, file_upload_id, progress_callback)

            # RÈGLE 18: Generate export files
            export_result = self._generate_export_files(df_processed, file_upload_id)

            # RÈGLE 19: Generate TCD (Tableau Croisé Dynamique) 
            pivot_result = self._generate_pivot_tables(file_upload_id)

            return {
                "success": True,
                "original_rows": len(df),
                "processed_rows": len(df_processed),
                "filtered_rows": len(df) - len(df_processed),
                "anomalies": self.anomalies,
                "statistics": stats,
                "database_save": save_result,
                "export_files": export_result,  # Export file generation result
                "pivot_tables": pivot_result  # TCD generation result
            }

        except Exception as e:
            logger.error(f"Error processing revenue journal: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_rows": 0,
                "processed_rows": 0,
                "anomalies": []
            }

    def process_account_descriptions(self, file_path: str, file_upload_id: int = None) -> Dict[str, Any]:
        """Process Account Descriptions file (Description Cpt Comptable.xlsx)"""
        try:
            df = self._read_file(file_path)
            logger.info(f"✅ Loaded {len(df)} account descriptions from file")
            logger.info(f"📋 File columns: {list(df.columns)}")
            
            # Show first few rows for debugging
            if len(df) > 0:
                logger.info(f"📊 First 3 rows preview:")
                for idx, row in df.head(3).iterrows():
                    logger.info(f"   Row {idx}: {dict(row)}")

            # Clean and validate
            df_processed = self._process_account_descriptions_data(df)
            logger.info(f"✅ After processing: {len(df_processed)} rows (removed {len(df) - len(df_processed)} duplicates)")

            # Save to database
            records = df_processed.to_dict('records')
            saved_count = 0
            created_count = 0
            updated_count = 0
            skipped_count = 0

            for idx, record in enumerate(records):
                from revenue_column_mapping import map_account_description_record
                mapped = map_account_description_record(
                    record, file_upload_id)

                if not mapped.get('cpt_comptable'):
                    logger.warning(f"⚠️ Row {idx}: No cpt_comptable value found")
                    skipped_count += 1
                    continue

                # Check if exists
                existing = self.db.query(AccountDescription).filter(
                    AccountDescription.cpt_comptable == mapped['cpt_comptable']
                ).first()

                if existing:
                    # Update
                    old_values = {
                        'description': existing.description_cpt_comptable,
                        'type_cpte': existing.type_cpte,
                    }
                    for key, value in mapped.items():
                        if key != 'created_at' and hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                    logger.debug(f"📝 Updated account '{mapped['cpt_comptable']}': {old_values} → {mapped.get('description_cpt_comptable')}")
                else:
                    # Create
                    account_desc = AccountDescription(**mapped)
                    self.db.add(account_desc)
                    self.db.flush()
                    created_count += 1
                    logger.debug(f"➕ Created account '{mapped['cpt_comptable']}': description='{mapped.get('description_cpt_comptable')}', type_cpte='{mapped.get('type_cpte')}', aut_bdg='{mapped.get('aut_bdg')}', aut_imp='{mapped.get('aut_imp')}', auxil='{mapped.get('auxil')}', let='{mapped.get('let')}'")

                saved_count += 1

            # Commit transaction
            try:
                self.db.flush()
                logger.info(f"🔄 Flushed session: {created_count} to create, {updated_count} to update")
                
                self.db.commit()
                logger.info(f"✅ Transaction committed successfully")
                
                # Verify save by counting records in DB
                total_in_db = self.db.query(AccountDescription).count()
                logger.info(f"📊 Total account descriptions in database after commit: {total_in_db}")
                
                # Show account descriptions from the file we just processed
                if file_upload_id:
                    recent_accounts = self.db.query(AccountDescription).filter(
                        AccountDescription.file_upload_id == file_upload_id
                    ).limit(10).all()
                    logger.info(f"📋 Found {len(recent_accounts)} account descriptions with file_upload_id={file_upload_id}:")
                    for acc in recent_accounts:
                        logger.info(f"   ✅ ID={acc.id}, cpt_comptable='{acc.cpt_comptable}', description='{acc.description_cpt_comptable}', type_cpte='{acc.type_cpte}', aut_bdg='{acc.aut_bdg}', aut_imp='{acc.aut_imp}', auxil='{acc.auxil}', let='{acc.let}'")
                else:
                    # Show latest 5 account descriptions
                    sample_accounts = self.db.query(AccountDescription).order_by(
                        AccountDescription.updated_at.desc()
                    ).limit(5).all()
                    logger.info(f"📋 Showing latest 5 account descriptions:")
                    for acc in sample_accounts:
                        logger.info(f"   ✅ ID={acc.id}, cpt_comptable='{acc.cpt_comptable}', description='{acc.description_cpt_comptable}', type_cpte='{acc.type_cpte}', aut_bdg='{acc.aut_bdg}', aut_imp='{acc.aut_imp}', auxil='{acc.auxil}', let='{acc.let}', file_upload_id={acc.file_upload_id}")
                
            except Exception as commit_error:
                logger.error(f"❌ Error committing transaction: {commit_error}")
                logger.exception(commit_error)
                self.db.rollback()
                raise

            logger.info(f"✅ Saved {saved_count} account descriptions: {created_count} created, {updated_count} updated, {skipped_count} skipped")

            return {
                "success": True,
                "processed_rows": len(df_processed),
                "saved_count": saved_count,
                "created_count": created_count,
                "updated_count": updated_count,
                "skipped_count": skipped_count
            }

        except Exception as e:
            logger.error(f"Error processing account descriptions: {e}")
            logger.exception(e)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def process_revenue_objectives(self, file_path: str, file_upload_id: int = None) -> Dict[str, Any]:
        """
        DEPRECATED: Process Revenue Objectives file (Objectif C.A.xlsx)

        This method processes the OLD annual objectives file format.
        Use process_dot_corporate() instead for monthly objectives (recommended).

        This method is kept for backward compatibility but will not be used
        for achievement rate calculations.
        """
        logger.warning("⚠️ DEPRECATED: process_revenue_objectives() is deprecated. Use process_dot_corporate() instead.")
        try:
            df = self._read_file(file_path)
            logger.info(f"✅ Loaded {len(df)} revenue objectives from file")
            logger.info(f"📋 File columns: {list(df.columns)}")
            
            # Show first few rows for debugging
            if len(df) > 0:
                logger.info(f"📊 First 3 rows preview:")
                for idx, row in df.head(3).iterrows():
                    logger.info(f"   Row {idx}: {dict(row)}")

            # Clean and validate
            df_processed = self._process_objectives_data(df)
            logger.info(f"✅ After processing: {len(df_processed)} rows (removed {len(df) - len(df_processed)} duplicates)")

            # Save to database
            records = df_processed.to_dict('records')
            saved_count = 0
            created_count = 0
            updated_count = 0
            skipped_count = 0

            for idx, record in enumerate(records):
                from revenue_column_mapping import map_revenue_objective_record
                mapped = map_revenue_objective_record(record, file_upload_id)

                if not mapped.get('dot_name'):
                    logger.warning(f"⚠️ Row {idx}: Skipping record with no DOT name: {record}")
                    skipped_count += 1
                    continue

                # Validate objectif_ca
                if mapped.get('objectif_ca') is None:
                    logger.warning(f"⚠️ Row {idx}: DOT '{mapped['dot_name']}' has no objectif_ca value")
                    skipped_count += 1
                    continue

                # Get or create DOT for Chiffre d'Affaires module
                dot = self._get_or_create_dot(
                    mapped['dot_name'],
                    f"DOT for {mapped['dot_name']} region"
                )
                mapped['dot_id'] = dot.id

                # Check if exists - use case-insensitive comparison
                # Try exact match first, then case-insensitive
                existing = self.db.query(RevenueObjective).filter(
                    RevenueObjective.dot_name == mapped['dot_name']
                ).first()
                
                if not existing:
                    # Try case-insensitive
                    existing = self.db.query(RevenueObjective).filter(
                        RevenueObjective.dot_name.ilike(mapped['dot_name'])
                    ).first()

                if existing:
                    # Update
                    old_value = float(existing.objectif_ca) if existing.objectif_ca else 0
                    new_value = float(mapped['objectif_ca']) if mapped['objectif_ca'] else 0
                    old_dot_name = existing.dot_name
                    logger.info(f"📝 Found existing objective for DOT '{mapped['dot_name']}' (DB: '{old_dot_name}')")
                    logger.info(f"   Updating: objectif_ca {old_value} → {new_value}")
                    
                    # Only update if values are different
                    if old_value != new_value or existing.dot_id != mapped.get('dot_id') or existing.file_upload_id != mapped.get('file_upload_id'):
                        for key, value in mapped.items():
                            if key != 'created_at' and hasattr(existing, key):
                                setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                        logger.info(f"   ✅ Values changed, updating record ID {existing.id}")
                    else:
                        logger.info(f"   ⏭️ Values unchanged, skipping update for record ID {existing.id}")
                    
                    updated_count += 1
                    logger.info(f"✅ Updated DOT '{mapped['dot_name']}': {old_value} → {new_value}")
                else:
                    # Create
                    logger.info(f"➕ Creating new objective for DOT '{mapped['dot_name']}' with objectif_ca = {mapped['objectif_ca']}")
                    objective = RevenueObjective(**mapped)
                    self.db.add(objective)
                    # Flush to get the ID
                    self.db.flush()
                    created_count += 1
                    logger.info(f"✅ Created DOT '{mapped['dot_name']}': objectif_ca = {mapped['objectif_ca']}, dot_id = {mapped['dot_id']}, new_id = {objective.id}")

                saved_count += 1

            # Commit transaction
            try:
                # Flush before commit to ensure all changes are in the session
                self.db.flush()
                logger.info(f"🔄 Flushed session: {created_count} to create, {updated_count} to update")
                
                self.db.commit()
                logger.info(f"✅ Transaction committed successfully")
                
                # Verify save by counting records in DB (new query after commit)
                total_in_db = self.db.query(RevenueObjective).count()
                logger.info(f"📊 Total revenue objectives in database after commit: {total_in_db}")
                
                # Show objectives from the file we just processed
                if file_upload_id:
                    recent_objectives = self.db.query(RevenueObjective).filter(
                        RevenueObjective.file_upload_id == file_upload_id
                    ).limit(10).all()
                    logger.info(f"📋 Found {len(recent_objectives)} objectives with file_upload_id={file_upload_id}:")
                    for obj in recent_objectives:
                        logger.info(f"   ✅ ID={obj.id}, dot_name='{obj.dot_name}', objectif_ca={obj.objectif_ca}, dot_id={obj.dot_id}")
                else:
                    # Show latest 5 objectives
                    sample_objectives = self.db.query(RevenueObjective).order_by(
                        RevenueObjective.updated_at.desc()
                    ).limit(5).all()
                    logger.info(f"📋 Showing latest 5 objectives (no file_upload_id provided):")
                    for obj in sample_objectives:
                        logger.info(f"   ✅ ID={obj.id}, dot_name='{obj.dot_name}', objectif_ca={obj.objectif_ca}, dot_id={obj.dot_id}, file_upload_id={obj.file_upload_id}")
                
            except Exception as commit_error:
                logger.error(f"❌ Error committing transaction: {commit_error}")
                logger.exception(commit_error)
                self.db.rollback()
                raise

            logger.info(f"✅ Saved {saved_count} revenue objectives: {created_count} created, {updated_count} updated, {skipped_count} skipped")

            return {
                "success": True,
                "processed_rows": len(df_processed),
                "saved_count": saved_count,
                "created_count": created_count,
                "updated_count": updated_count,
                "skipped_count": skipped_count
            }

        except Exception as e:
            logger.error(f"Error processing revenue objectives: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def process_dot_corporate(self, file_path: str, file_upload_id: int = None) -> Dict[str, Any]:
        """Process DOT Corporate revenue file with monthly data"""
        try:
            # Read file - Excel stores numbers as numbers, so pandas will parse them
            # We'll handle the parsing in the parse_french_number function
            from pathlib import Path
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.csv':
                df = pd.read_csv(file_path, dtype=str, low_memory=False)
            elif file_ext in ['.xlsx', '.xls']:
                # Read Excel normally - pandas will parse numbers
                # We'll handle French format in the parser
                df = pd.read_excel(file_path, engine='openpyxl' if file_ext == '.xlsx' else 'xlrd')
            else:
                df = self._read_file(file_path)
            
            logger.info(f"✅ Loaded {len(df)} rows from DOT Corporate file")
            logger.info(f"📋 File columns: {list(df.columns)}")
            
            # Show first few rows for debugging
            if len(df) > 0:
                logger.info(f"📊 First 3 rows preview:")
                for idx, row in df.head(3).iterrows():
                    logger.info(f"   Row {idx}: {dict(row)}")

            # Expected columns: DOT, Jan, fév, mars, Avril, Mai, Juin, Juillet, aout, Sept, Oct, Nov, Déc
            # Find DOT column (first column)
            dot_col = None
            for col in df.columns:
                col_lower = str(col).strip().lower()
                if col_lower in ['dot', 'd.o.t', 'direction']:
                    dot_col = col
                    break
            
            if not dot_col:
                # Use first column as DOT
                dot_col = df.columns[0]
                logger.info(f"⚠️ DOT column not found, using first column: '{dot_col}'")

            # Map month columns (case-insensitive)
            month_mapping = {
                'jan': 'january',
                'janvier': 'january',
                'fév': 'february',
                'février': 'february',
                'fev': 'february',
                'mars': 'march',
                'avril': 'april',
                'mai': 'may',
                'juin': 'june',
                'juillet': 'july',
                'aout': 'august',
                'août': 'august',
                'sept': 'september',
                'septembre': 'september',
                'oct': 'october',
                'octobre': 'october',
                'nov': 'november',
                'novembre': 'november',
                'déc': 'december',
                'décembre': 'december',
                'dec': 'december'
            }

            # Find month columns
            month_cols = {}
            for col in df.columns:
                col_lower = str(col).strip().lower()
                for key, value in month_mapping.items():
                    if key in col_lower:
                        month_cols[value] = col
                        break

            logger.info(f"📅 Found month columns: {month_cols}")

            # Process and save records
            saved_count = 0
            created_count = 0
            updated_count = 0
            skipped_count = 0

            for idx, row in df.iterrows():
                dot_name = str(row[dot_col]).strip() if pd.notna(row[dot_col]) else None
                
                if not dot_name or dot_name.lower() in ['nan', 'none', '']:
                    logger.warning(f"⚠️ Row {idx}: Skipping record with no DOT name")
                    skipped_count += 1
                    continue

                # Get or create DOT for Chiffre d'Affaires module
                dot = self._get_or_create_dot(
                    dot_name,
                    f"DOT Corporate for {dot_name}"
                )

                # Helper function to parse French number format
                def parse_french_number(value):
                    """Parse French number format
                    
                    Handles two cases:
                    1. French format string: '5.266.666,67' -> 5266666.67
                    2. Already parsed float: 5266666.666666667 -> 5266666.67 (round to 2 decimals)
                    """
                    if pd.isna(value) or value == '':
                        return None
                    try:
                        # If it's already a numeric type (float/int), pandas parsed it
                        if isinstance(value, (int, float)):
                            # Round to 2 decimal places and validate range
                            result = round(float(value), 2)
                            max_value = 9999999999999.99
                            if abs(result) > max_value:
                                logger.warning(f"⚠️ Value {result} exceeds NUMERIC(15,2) range, clamping to {max_value}")
                                result = max_value if result > 0 else -max_value
                            return result
                        
                        # Convert to string for parsing
                        str_val = str(value).strip()
                        if not str_val or str_val.lower() in ['nan', 'none', '']:
                            return None
                        
                        # Check if it's French format (has comma as decimal separator)
                        if ',' in str_val:
                            # French format: dots = thousands, comma = decimal
                            # Example: "5.266.666,67" -> remove dots -> "5266666,67" -> replace comma -> "5266666.67"
                            str_val = str_val.replace('.', '').replace(',', '.')
                        # If no comma, assume it's already in standard format (dots removed by pandas)
                        # Just parse as float
                        
                        # Remove any remaining non-numeric characters except minus and dot
                        import re
                        str_val = re.sub(r'[^\d\.\-]', '', str_val)
                        
                        if not str_val:
                            return None
                        
                        result = round(float(str_val), 2)
                        
                        # Validate result is within NUMERIC(15,2) range
                        max_value = 9999999999999.99
                        if abs(result) > max_value:
                            logger.warning(f"⚠️ Value {result} exceeds NUMERIC(15,2) range, clamping to {max_value}")
                            result = max_value if result > 0 else -max_value
                        
                        return result
                    except (ValueError, TypeError) as e:
                        logger.warning(f"⚠️ Failed to parse number '{value}': {e}")
                        return None

                # Extract monthly values
                def get_month_value(month_name):
                    col_name = month_cols.get(month_name)
                    if col_name and col_name in row.index:
                        return parse_french_number(row[col_name])
                    return None

                # Get current year for filtering
                current_year = datetime.utcnow().year

                record_data = {
                    'file_upload_id': file_upload_id,
                    'dot_id': dot.id,
                    'dot_name': dot_name,
                    'year': current_year,
                    'january': get_month_value('january'),
                    'february': get_month_value('february'),
                    'march': get_month_value('march'),
                    'april': get_month_value('april'),
                    'may': get_month_value('may'),
                    'june': get_month_value('june'),
                    'july': get_month_value('july'),
                    'august': get_month_value('august'),
                    'september': get_month_value('september'),
                    'october': get_month_value('october'),
                    'november': get_month_value('november'),
                    'december': get_month_value('december')
                }

                # Check if record exists (by dot_name, year, and file_upload_id)
                # This allows multiple years of data for the same DOT
                existing = self.db.query(RevenueDOTCorporate).filter(
                    RevenueDOTCorporate.dot_name == dot_name,
                    RevenueDOTCorporate.year == current_year,
                    RevenueDOTCorporate.file_upload_id == file_upload_id
                ).first()

                if existing:
                    # Update existing record
                    for key, value in record_data.items():
                        if key != 'created_at' and hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                    logger.debug(f"📝 Updated DOT Corporate '{dot_name}'")
                else:
                    # Create new record
                    revenue_dot = RevenueDOTCorporate(**record_data)
                    self.db.add(revenue_dot)
                    self.db.flush()
                    created_count += 1
                    logger.debug(f"➕ Created DOT Corporate '{dot_name}'")

                saved_count += 1

            # Commit transaction
            try:
                self.db.flush()
                logger.info(f"🔄 Flushed session: {created_count} to create, {updated_count} to update")
                
                self.db.commit()
                logger.info(f"✅ Transaction committed successfully")
                
                # Verify save
                total_in_db = self.db.query(RevenueDOTCorporate).count()
                logger.info(f"📊 Total DOT Corporate records in database after commit: {total_in_db}")
                
            except Exception as commit_error:
                logger.error(f"❌ Error committing transaction: {commit_error}")
                logger.exception(commit_error)
                self.db.rollback()
                raise

            logger.info(f"✅ Saved {saved_count} DOT Corporate records: {created_count} created, {updated_count} updated, {skipped_count} skipped")

            return {
                "success": True,
                "processed_rows": len(df),
                "saved_count": saved_count,
                "created_count": created_count,
                "updated_count": updated_count,
                "skipped_count": skipped_count
            }

        except Exception as e:
            logger.error(f"Error processing DOT Corporate file: {e}")
            logger.exception(e)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e),
                "processed_rows": 0,
                "saved_count": 0
            }

    def _read_file(self, file_path: str) -> pd.DataFrame:
        """Read CSV or Excel file, with support for HTML files masquerading as .xls"""
        from pathlib import Path
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.csv':
            return pd.read_csv(file_path, low_memory=False)
        elif file_ext == '.xlsx':
            # Read Excel file normally - pandas will parse numbers
            # French format numbers (with commas) will be preserved as strings if Excel stored them as text
            # If Excel stored them as numbers, pandas will convert them correctly
            # We'll handle French format conversion in clean_numeric_fields via smart_parse_numeric
            return pd.read_excel(file_path, engine='openpyxl')
        elif file_ext == '.xls':
            # .xls files might be HTML masquerading as Excel
            try:
                # First, try to read as real Excel file
                logger.info(f"📖 Attempting to read {file_path} as Excel file")
                return pd.read_excel(file_path, engine='xlrd')
            except Exception as e:
                # If that fails, try HTML parsing (some systems export HTML with .xls extension)
                logger.warning(f"⚠️ Failed to read .xls as Excel: {str(e)}")
                logger.info(f"📖 Attempting to read {file_path} as HTML table")
                try:
                    # CRITICAL FIX: Read HTML table and convert all numeric columns to object dtype to preserve French format
                    # This prevents pandas from auto-converting "4320000,00" to 43200000.0
                    html_tables_raw = pd.read_html(file_path, header=None)
                    if not html_tables_raw:
                        raise ValueError("No HTML tables found in file")

                    logger.info(f"✅ Found {len(html_tables_raw)} HTML table(s) in file")

                    # Find the table with the most columns (likely the data table)
                    # For revenue journal, we expect 30 columns
                    best_table = None
                    best_table_idx = -1
                    max_columns = 0

                    for idx, table in enumerate(html_tables_raw):
                        if len(table.columns) > max_columns:
                            max_columns = len(table.columns)
                            best_table = table
                            best_table_idx = idx

                    if best_table is None:
                        raise ValueError("No suitable HTML table found")

                    # CRITICAL: Convert all columns to string IMMEDIATELY to prevent pandas number conversion
                    # Pandas has already parsed numbers at this point, so we need to read HTML content as text
                    import re
                    from io import StringIO

                    # Re-read the HTML as raw text to preserve French number format
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        html_content = f.read()

                    # Replace French decimal commas with a temporary placeholder in numeric contexts
                    # Pattern: digits followed by comma followed by exactly 2 digits (decimal)
                    html_content_fixed = re.sub(r'(\d+),(\d{2})(?!\d)', r'\1DECIMALSEP\2', html_content)

                    # Now read the modified HTML
                    html_tables_fixed = pd.read_html(StringIO(html_content_fixed), header=None)
                    best_table = max(html_tables_fixed, key=lambda t: len(t.columns))

                    # Convert DECIMALSEP back to dots in all string columns
                    for col in best_table.columns:
                        best_table[col] = best_table[col].astype(str).str.replace('DECIMALSEP', '.')

                    logger.info(f"📊 Using HTML table {best_table_idx} with {len(best_table.columns)} columns and {len(best_table)} rows")
                    logger.info(f"✅ Fixed French decimal separators (comma → dot) before pandas parsing")
                    
                    # Find header row (search first 20 rows)
                    header_row = self._find_header_row_for_revenue_journal(best_table.head(20).reset_index(drop=True))
                    
                    if header_row is not None:
                        logger.info(f"✅ Found header row at index {header_row}")
                        # Extract headers from the detected row
                        headers = best_table.iloc[header_row].astype(str).tolist()
                        # Data starts after header
                        df = best_table.iloc[header_row + 1:].copy()
                        df.columns = headers
                        df.reset_index(drop=True, inplace=True)
                        logger.info(f"✅ Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
                        return df
                    else:
                        # If no header row found, assume first row is header
                        logger.warning("⚠️ No clear header row found, using row 0 as header")
                        df = best_table.iloc[1:].copy()
                        df.columns = best_table.iloc[0].astype(str).tolist()
                        df.reset_index(drop=True, inplace=True)
                        return df
                        
                except Exception as html_error:
                    logger.error(f"❌ Failed to read file as HTML: {str(html_error)}")
                    raise ValueError(f"Could not read file as Excel or HTML: {str(e)}. HTML error: {str(html_error)}")
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
    
    def _find_header_row_for_revenue_journal(self, df: pd.DataFrame) -> Optional[int]:
        """Find the header row in a DataFrame by looking for revenue journal column names"""
        # Expected revenue journal columns
        expected_headers = [
            'Org Name', 'Origine', 'N Fact', 'Typ Fact', 'Date Fact',
            'N Client', 'Client', 'Delai Paie', 'Devise', 'Obj Fact',
            'Cpt Comptable', 'Date facture GL', 'Date GL', 'Periode de facturation',
            'Reference', 'Termine Flag', 'Tax Amount', 'Creer Par', 'N Ligne',
            'Description (ligne de produit)', 'Uom', 'Qte', 'Prix Uni', 'Taux Change',
            'Mnt Ht', 'Tax', 'Mnt Tax', 'Mnt Ttc', 'Memo Line Id', 'Chiffre Aff Exe Dzd'
        ]
        
        # Normalize function for comparison
        def normalize(s):
            return str(s).strip().lower().replace('_', ' ').replace('-', ' ')
        
        normalized_expected = [normalize(h) for h in expected_headers]
        
        # Search first 20 rows for header row
        max_rows_to_check = min(20, len(df))
        best_match_row = None
        best_match_count = 0
        
        for row_idx in range(max_rows_to_check):
            row_values = [normalize(str(val)) for val in df.iloc[row_idx].values if pd.notna(val)]
            match_count = sum(1 for expected in normalized_expected if any(expected in val or val in expected for val in row_values))
            
            if match_count > best_match_count:
                best_match_count = match_count
                best_match_row = row_idx
            
            # If we found at least 5 matching headers, consider it a good match
            if match_count >= 5:
                logger.info(f"✅ Found header row at index {row_idx} with {match_count} matching headers")
                return row_idx
        
        # Return best match if we found at least 3 matches
        if best_match_count >= 3:
            logger.info(f"✅ Found best header row at index {best_match_row} with {best_match_count} matching headers")
            return best_match_row
        
        return None

    def _apply_journal_processing_rules(self, df: pd.DataFrame,
                                          progress_callback=None) -> pd.DataFrame:
        """Apply all processing rules to revenue journal data (in order)"""
        original_count = len(df)
        logger.info(f"Starting revenue journal processing with {original_count} rows")
        
        # Track Chiffre Aff Exe Dzd sum at each step for debugging
        def log_ca_sum(df, step_name):
            ca_col = self._find_column(df, ['Chiffre Aff Exe Dzd', 'revenue dzd'])
            if ca_col:
                try:
                    # Ensure numeric values before summing
                    ca_numeric = pd.to_numeric(df[ca_col], errors='coerce')
                    ca_sum = ca_numeric.sum()
                    ca_non_null = ca_numeric.notna().sum()
                    ca_null = ca_numeric.isna().sum()
                    ca_zero = (ca_numeric == 0).sum() if ca_non_null > 0 else 0
                    # Format sum safely (handle NaN/None)
                    if pd.isna(ca_sum):
                        ca_sum_str = "NaN"
                    else:
                        ca_sum_str = f"{ca_sum:,.2f}"
                    logger.info(f"   📊 {step_name}: CA Sum = {ca_sum_str}, Non-null = {ca_non_null}, NULL = {ca_null}, Zero = {ca_zero}")
                    return ca_sum if not pd.isna(ca_sum) else None
                except Exception as e:
                    logger.warning(f"   ⚠️ Error calculating CA sum at {step_name}: {e}")
                    return None
            return None
        
        initial_ca_sum = log_ca_sum(df, "Initial")

        # 0. Remove header-like rows (rows that match expected column names)
        df = self._filter_header_rows(df)
        logger.info(f"After header row filter: {len(df)} rows")
        log_ca_sum(df, "After header filter")

        # 1. Garder que le tableau (keep only table data - skip if needed)

        # 1a. CROSS-REFERENCING FIRST: Matcher avec Description Cpt Comptable
        df = self._match_account_descriptions(df)
        logger.info(f"Matched account descriptions")
        log_ca_sum(df, "After account matching")

        # 1b. CROSS-REFERENCING FIRST: Matcher avec Objectif C.A
        df = self._match_revenue_objectives(df)
        logger.info(f"Matched revenue objectives")
        log_ca_sum(df, "After objective matching")

        # 2. Org Name: Supprimer toutes les lignes contenant AT_SIEGE
        df = self._filter_at_siege(df)
        logger.info(f"After AT_SIEGE filter: {len(df)} rows")
        log_ca_sum(df, "After AT_SIEGE filter")

        # 3. Org Name: Remplacer DOT_ par vide
        df = self._clean_org_name_dot(df)

        # 4. Org Name: Remplacer – et _ par espace
        df = self._clean_org_name_separators(df)

        # 5. Trier par Org Name, Type Fact et N Fact
        df = self._sort_by_org_type_invoice(df)
        logger.info(f"Sorted by Org Name, Type Fact, N Fact")

        # 6. Si Cpt Comptable contenant la lettre A et Description ne commence pas par @
        #    => mettre comme Anomalie
        df = self._detect_anomalies(df)
        logger.info(f"Detected {len(self.anomalies)} anomalies")

        # 7. Cpt Comptable : Supprimer toutes les lignes contenant la lettre A
        df = self._filter_cpt_comptable_with_a(df)
        logger.info(f"After Cpt Comptable filter: {len(df)} rows")
        log_ca_sum(df, "After Cpt Comptable filter")

        # 8. Date GL : Garder les lignes ayant l'année la plus récente
        # NOTE: Year filter is now optional - it will log what years are found but won't filter by default
        # Uncomment the line below to enable year filtering
        # df = self._keep_most_recent_year(df)
        
        # Log year distribution without filtering
        date_col = self._find_column(df, ['Date GL', 'gl date'])
        if date_col:
            try:
                import pandas as pd
                df_temp = df.copy()
                df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors='coerce', dayfirst=True)
                years = df_temp[date_col].dt.year.dropna()
                if len(years) > 0:
                    unique_years = sorted(years.unique())
                    year_counts = years.value_counts().sort_index()
                    logger.info(f"📅 Years found in journal table (no filtering applied): {unique_years}")
                    logger.info(f"📅 Year distribution: {dict(year_counts)}")
                    logger.info(f"📅 Total rows across all years: {len(df)}")
            except Exception as e:
                logger.debug(f"Could not analyze year distribution: {e}")
        
        logger.info(f"After year filter (disabled): {len(df)} rows")
        log_ca_sum(df, "After year filter (disabled)")

        # 9-13. Clean numeric fields (remove ".")
        df = self._clean_numeric_fields(df)
        log_ca_sum(df, "After numeric cleaning")

        # 14. Mettre le séparateur de millier avec deux chiffres après la virgule
        # (This is for display/export, not for processing)

        # 15. Ajouter une colonne TVA (=Mnt Ttc/Mnt Ht)
        df = self._calculate_tva(df)

        # 16. Ajouter une colonne Chiffre Aff Exe Dzd TTC (=Chiffre Aff Exe Dzd * TVA)
        df = self._calculate_ca_ttc(df)

        # 19. Ajouter une colonne Taux de réalisation C.A
        df = self._calculate_achievement_rate(df)

        # 20. Remove duplicate rows based on key fields
        df = self._remove_duplicate_rows(df)
        logger.info(f"After duplicate removal: {len(df)} rows")
        final_ca_sum = log_ca_sum(df, "After duplicate removal (FINAL)")

        # 21. Validate final result - check for rows that should have been filtered
        self._validate_filtered_data(df)
        
        # Log summary of CA sum changes
        if initial_ca_sum is not None and final_ca_sum is not None:
            try:
                ca_loss = initial_ca_sum - final_ca_sum
                ca_loss_pct = (ca_loss / initial_ca_sum * 100) if initial_ca_sum != 0 else 0
                logger.info(f"📊 CA Sum Summary: Initial = {initial_ca_sum:,.2f}, Final = {final_ca_sum:,.2f}, Loss = {ca_loss:,.2f} ({ca_loss_pct:.2f}%)")
            except (TypeError, ValueError) as e:
                logger.warning(f"⚠️ Could not calculate CA sum summary: {e}")
            
            # Check for rows with NULL or zero CA values
            ca_col = self._find_column(df, ['Chiffre Aff Exe Dzd', 'revenue dzd'])
            if ca_col:
                null_ca = df[df[ca_col].isna()]
                zero_ca = df[(df[ca_col] == 0) & df[ca_col].notna()]
                if len(null_ca) > 0:
                    logger.warning(f"⚠️ Found {len(null_ca)} rows with NULL Chiffre Aff Exe Dzd")
                    org_col = self._find_column(df, ['Org Name', 'organisation'])
                    for idx, row in null_ca.head(10).iterrows():
                        org_name = row.get(org_col, 'N/A') if org_col else 'N/A'
                        logger.warning(f"   Row {idx}: Org Name = '{org_name}', CA = NULL")
                if len(zero_ca) > 0:
                    logger.warning(f"⚠️ Found {len(zero_ca)} rows with ZERO Chiffre Aff Exe Dzd")
                    if len(zero_ca) <= 20:
                        org_col = self._find_column(df, ['Org Name', 'organisation'])
                        for idx, row in zero_ca.head(10).iterrows():
                            org_name = row.get(org_col, 'N/A') if org_col else 'N/A'
                            logger.warning(f"   Row {idx}: Org Name = '{org_name}', CA = 0")

        self.filtered_count = original_count - len(df)
        logger.info(
            f"Processing complete: {len(df)} rows remaining, {self.filtered_count} filtered")

        return df

    def _filter_at_siege(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows where Org Name contains 'AT_SIEGE' (or variations)"""
        org_name_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_name_col:
            original = len(df)
            # Check for various AT_SIEGE patterns: AT_SIEGE, AT-SIEGE, AT SIEGE, etc.
            # Normalize by replacing separators and checking for "ATSIEGE" pattern
            org_name_str = df[org_name_col].astype(str).str.upper()
            # Replace common separators with nothing to normalize
            normalized = org_name_str.str.replace(r'[_\s\-]+', '', regex=True)
            # Check if normalized contains "ATSIEGE"
            mask = normalized.str.contains('ATSIEGE', case=False, na=False)
            filtered_count = mask.sum()

            # Calculate CA sum lost from filtered rows
            ca_col = self._find_column(df, ['Chiffre Aff Exe Dzd', 'revenue dzd'])
            if ca_col and filtered_count > 0:
                try:
                    filtered_rows = df.loc[mask]
                    ca_numeric = pd.to_numeric(filtered_rows[ca_col], errors='coerce')
                    filtered_ca_sum = ca_numeric.sum()
                    if not pd.isna(filtered_ca_sum) and filtered_ca_sum != 0:
                        logger.info(f"   💰 CA Sum lost from AT_SIEGE filter: {filtered_ca_sum:,.2f} DZD")
                except Exception as e:
                    logger.debug(f"   Could not calculate CA sum lost from AT_SIEGE filter: {e}")

            # Capture sample before filtering
            if filtered_count > 0 and filtered_count <= 10:
                filtered_sample = df.loc[mask, org_name_col].head(5).tolist()

            df = df[~mask]
            filtered = original - len(df)
            if filtered > 0:
                logger.info(f"Filtered {filtered} rows containing AT_SIEGE (or variations)")
                # Log sample of filtered rows for debugging
                if filtered_count <= 10 and filtered_count > 0:
                    logger.info(f"   Sample filtered Org Names: {filtered_sample}")
        return df

    def _clean_org_name_dot(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove 'DOT_' and 'DOT ' prefix from Org Name"""
        org_name_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_name_col:
            # Remove both "DOT_" and "DOT " (with underscore or space)
            # Use regex to match at the beginning of the string
            df.loc[:, org_name_col] = df[org_name_col].astype(str).str.replace(
                r'^DOT[_\s]+', '', case=False, regex=True).str.strip()
        return df

    def _clean_org_name_separators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Replace -, – and _ with spaces in Org Name"""
        org_name_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_name_col:
            df.loc[:, org_name_col] = df[org_name_col].astype(str).str.replace(
                '-', ' ').str.replace('–', ' ').str.replace('_', ' ').str.replace('  ', ' ').str.strip()
        return df

    def _filter_reprise(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        NOUVELLE RÈGLE: Supprimer toutes les lignes contenant 'reprise' (case-insensitive)
        Recherche dans toutes les colonnes textuelles
        """
        original = len(df)

        # Columns to search for 'reprise'
        text_columns = []
        for col in df.columns:
            if df[col].dtype == 'object':  # String columns
                text_columns.append(col)

        if text_columns:
            # Create mask to filter rows containing 'reprise' in ANY column
            mask = pd.Series([False] * len(df), index=df.index)
            for col in text_columns:
                mask |= df[col].astype(str).str.contains('reprise', case=False, na=False)

            # Keep rows that DON'T contain 'reprise'
            df = df[~mask]

            filtered = original - len(df)
            if filtered > 0:
                logger.info(f"Filtered {filtered} rows containing 'reprise'")

        return df

    def _fix_specific_dot_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        NOUVELLE RÈGLE: Corriger des noms de DOT spécifiques
        - BORD-BOU-ARRERIDJ → BORD BOU ARRERIDJ
        """
        org_name_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_name_col:
            # Fix specific DOT name
            df.loc[:, org_name_col] = df[org_name_col].astype(str).str.replace(
                'BORD-BOU-ARRERIDJ', 'BORD BOU ARRERIDJ', case=False, regex=False
            )
            # Also fix with underscores
            df.loc[:, org_name_col] = df[org_name_col].astype(str).str.replace(
                'BORD_BOU_ARRERIDJ', 'BORD BOU ARRERIDJ', case=False, regex=False
            )
            logger.info("Fixed specific DOT names (BORD-BOU-ARRERIDJ)")
        return df

    def _sort_by_org_type_invoice(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sort by Org Name, Type Fact, N Fact"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers
        return RevenueProcessingHelpers.sort_by_org_type_invoice(df)

    def _detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect anomalies where Cpt Comptable contains 'A' and Description doesn't start with '@'"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers

        cpt_col = self._find_column(
            df, ['Cpt Comptable', 'compte comptable'])
        desc_col = self._find_column(
            df, ['Description (ligne de produit)', 'description ligne'])

        if not cpt_col or not desc_col:
            return df

        anomaly_rows = []
        for idx, row in df.iterrows():
            anomaly_reason = RevenueProcessingHelpers.detect_anomalies_in_row(
                row, cpt_col, desc_col)
            if anomaly_reason:
                # Store full row data as dictionary for complete export
                # Use the actual DataFrame column names to preserve all data
                full_row_data = {}
                import json
                import numpy as np
                import pandas as pd
                
                # Iterate through all columns in the DataFrame to capture ALL data
                for col_name in df.columns:
                    value = row[col_name]
                    # Convert any pandas/numpy types to native Python types for JSON serialization
                    if pd.isna(value):
                        full_row_data[col_name] = None
                    elif isinstance(value, (np.integer, np.floating)):
                        full_row_data[col_name] = float(value) if isinstance(value, np.floating) else int(value)
                    elif isinstance(value, (pd.Timestamp, pd.DatetimeIndex)):
                        full_row_data[col_name] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
                    elif isinstance(value, (pd.Series, pd.DataFrame)):
                        # Skip nested DataFrames/Series
                        continue
                    elif hasattr(value, '__tablename__'):
                        # Handle SQLAlchemy ORM objects (like AccountDescription)
                        # Convert to dict with just the ID to avoid serialization errors
                        full_row_data[col_name] = {"id": getattr(value, 'id', None)} if hasattr(value, 'id') else str(value)
                    else:
                        full_row_data[col_name] = value
                
                # Also get key fields using column finder for backward compatibility
                org_col = self._find_column(df, ['Org Name', 'organisation'])
                n_fact_col = self._find_column(df, ['N Fact', 'invoice'])
                
                self.anomalies.append({
                    "type": "Chiffre d'Affaires AR DOT",
                    "org_name": row[org_col] if org_col and org_col in row.index else (full_row_data.get(org_col, 'N/A') if org_col else 'N/A'),
                    "n_fact": row[n_fact_col] if n_fact_col and n_fact_col in row.index else (full_row_data.get(n_fact_col, 'N/A') if n_fact_col else 'N/A'),
                    "reason": anomaly_reason,
                    "cpt_comptable": row[cpt_col] if cpt_col in row.index else full_row_data.get(cpt_col, 'N/A'),
                    "description": row[desc_col] if desc_col in row.index else full_row_data.get(desc_col, 'N/A'),
                    "full_row_data": full_row_data  # Store complete row data with ALL columns
                })
                anomaly_rows.append(idx)

        return df

    def _filter_cpt_comptable_with_a(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows where Cpt Comptable contains letter 'A'"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers
        cpt_col = self._find_column(
            df, ['Cpt Comptable', 'compte comptable'])
        if cpt_col:
            original = len(df)
            ca_col = self._find_column(df, ['Chiffre Aff Exe Dzd', 'revenue dzd'])
            
            # Calculate CA sum before filtering
            if ca_col:
                try:
                    mask = df[cpt_col].astype(str).str.contains('A', case=False, na=False)
                    filtered_rows = df[mask]
                    ca_numeric = pd.to_numeric(filtered_rows[ca_col], errors='coerce')
                    filtered_ca_sum = ca_numeric.sum()
                    if not pd.isna(filtered_ca_sum) and filtered_ca_sum != 0:
                        logger.info(f"   💰 CA Sum lost from Cpt Comptable filter: {filtered_ca_sum:,.2f} DZD")
                except Exception as e:
                    logger.debug(f"   Could not calculate CA sum lost from Cpt Comptable filter: {e}")
            
            return RevenueProcessingHelpers.filter_cpt_comptable_with_a(df, cpt_col)
        return df

    def _keep_most_recent_year(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only most recent year in Date GL"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers
        date_col = self._find_column(df, ['Date GL', 'gl date'])
        if date_col:
            return RevenueProcessingHelpers.keep_most_recent_year(df, date_col)
        return df

    def _filter_header_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows that look like header rows (contain expected column names)"""
        if len(df) == 0:
            return df
        
        # Expected revenue journal column names (normalized)
        expected_headers = [
            'org name', 'origine', 'n fact', 'typ fact', 'date fact',
            'n client', 'client', 'delai paie', 'devise', 'obj fact',
            'cpt comptable', 'date facture gl', 'date gl', 'periode de facturation',
            'reference', 'termine flag', 'tax amount', 'creer par', 'n ligne',
            'description (ligne de produit)', 'uom', 'qte', 'prix uni', 'taux change',
            'mnt ht', 'tax', 'mnt tax', 'mnt ttc', 'memo line id', 'chiffre aff exe dzd'
        ]
        
        def normalize(s):
            return str(s).strip().lower().replace('_', ' ').replace('-', ' ')
        
        def is_header_row(row):
            """Check if a row looks like a header row"""
            row_values = [normalize(str(val)) for val in row.values if pd.notna(val)]
            # Count how many values match expected headers exactly or as substring
            matches = sum(1 for val in row_values if any(header in val or val in header for header in expected_headers))
            # Require at least 6 matches to be confident it's a header row (not legitimate data)
            # Also check if most values are exact header matches (more strict)
            exact_matches = sum(1 for val in row_values if val in expected_headers)
            # If 6+ matches OR 4+ exact matches, it's likely a header row
            return matches >= 6 or exact_matches >= 4
        
        original = len(df)
        # Filter out rows that look like headers
        mask = df.apply(is_header_row, axis=1)
        filtered_count = mask.sum()
        
        # Capture sample before filtering
        if filtered_count > 0 and filtered_count <= 10:
            filtered_sample = df.loc[mask].head(5)
            sample_org_names = filtered_sample.get(self._find_column(df, ['Org Name', 'organisation']), pd.Series()).tolist() if len(filtered_sample) > 0 else []
        
        df = df[~mask]
        filtered = original - len(df)
        
        if filtered > 0:
            logger.info(f"Filtered {filtered} header-like rows")
            # Log sample of filtered rows for debugging
            if filtered_count <= 10 and filtered_count > 0 and len(sample_org_names) > 0:
                logger.info(f"   Sample filtered Org Names: {sample_org_names[:3]}")
        
        return df

    def _validate_filtered_data(self, df: pd.DataFrame) -> None:
        """Validate that no rows that should be filtered are still present"""
        if len(df) == 0:
            return
        
        issues_found = []
        
        # Check for header-like rows that slipped through
        expected_headers = [
            'org name', 'origine', 'n fact', 'typ fact', 'date fact',
            'n client', 'client', 'delai paie', 'devise', 'obj fact',
            'cpt comptable', 'date facture gl', 'date gl', 'periode de facturation',
            'reference', 'termine flag', 'tax amount', 'creer par', 'n ligne',
            'description (ligne de produit)', 'uom', 'qte', 'prix uni', 'taux change',
            'mnt ht', 'tax', 'mnt tax', 'mnt ttc', 'memo line id', 'chiffre aff exe dzd'
        ]
        
        def normalize(s):
            return str(s).strip().lower().replace('_', ' ').replace('-', ' ')
        
        def is_header_row(row):
            row_values = [normalize(str(val)) for val in row.values if pd.notna(val)]
            matches = sum(1 for val in row_values if any(header in val or val in header for header in expected_headers))
            exact_matches = sum(1 for val in row_values if val in expected_headers)
            return matches >= 6 or exact_matches >= 4
        
        header_mask = df.apply(is_header_row, axis=1)
        if header_mask.any():
            header_rows = df[header_mask]
            issues_found.append(f"Found {len(header_rows)} header-like rows that should have been filtered")
            logger.warning(f"⚠️ VALIDATION: {issues_found[-1]}")
            org_col = self._find_column(df, ['Org Name', 'organisation'])
            for idx, row in header_rows.head(5).iterrows():
                org_name = row.get(org_col, 'N/A') if org_col else 'N/A'
                logger.warning(f"   Row {idx}: Org Name = '{org_name}', Row values: {list(row.values)[:5]}")
        
        # Check for AT_SIEGE variations
        org_name_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_name_col:
            org_name_str = df[org_name_col].astype(str).str.upper()
            normalized = org_name_str.str.replace(r'[_\s\-]+', '', regex=True)
            at_siege_mask = normalized.str.contains('ATSIEGE', case=False, na=False)
            if at_siege_mask.any():
                at_siege_rows = df[at_siege_mask]
                issues_found.append(f"Found {len(at_siege_rows)} rows with AT_SIEGE variations")
                logger.warning(f"⚠️ VALIDATION: {issues_found[-1]}")
                for idx, row in at_siege_rows.head(5).iterrows():
                    logger.warning(f"   Row {idx}: Org Name = '{row.get(org_name_col, 'N/A')}'")
        
        # Check for Cpt Comptable with 'A'
        cpt_col = self._find_column(df, ['Cpt Comptable', 'compte comptable'])
        if cpt_col:
            cpt_with_a = df[cpt_col].astype(str).str.contains('A', case=False, na=False)
            if cpt_with_a.any():
                cpt_a_rows = df[cpt_with_a]
                issues_found.append(f"Found {len(cpt_a_rows)} rows with 'A' in Cpt Comptable")
                logger.warning(f"⚠️ VALIDATION: {issues_found[-1]}")
                for idx, row in cpt_a_rows.head(5).iterrows():
                    logger.warning(f"   Row {idx}: Cpt Comptable = '{row.get(cpt_col, 'N/A')}'")
        
        # Check for invalid dates or wrong year
        date_col = self._find_column(df, ['Date GL', 'gl date'])
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
            valid_years = df[date_col].dt.year.dropna()
            if len(valid_years) > 0:
                most_recent_year = valid_years.max()
                wrong_year_mask = (df[date_col].dt.year != most_recent_year) & df[date_col].notna()
                invalid_date_mask = df[date_col].isna()
                
                if wrong_year_mask.any():
                    wrong_year_rows = df[wrong_year_mask]
                    issues_found.append(f"Found {len(wrong_year_rows)} rows with wrong year (not {most_recent_year})")
                    logger.warning(f"⚠️ VALIDATION: {issues_found[-1]}")
                    for idx, row in wrong_year_rows.head(5).iterrows():
                        logger.warning(f"   Row {idx}: Date GL = '{row.get(date_col, 'N/A')}'")
                
                if invalid_date_mask.any():
                    invalid_date_rows = df[invalid_date_mask]
                    issues_found.append(f"Found {len(invalid_date_rows)} rows with invalid dates")
                    logger.warning(f"⚠️ VALIDATION: {issues_found[-1]}")
                    for idx, row in invalid_date_rows.head(5).iterrows():
                        logger.warning(f"   Row {idx}: Date GL = '{row.get(date_col, 'N/A')}'")
        
        # Check for duplicates that should have been removed
        key_fields = []
        field_mappings = [
            ('Org Name', 'org_name'),
            ('N Fact', 'n_fact'),
            ('Typ Fact', 'typ_fact'),
            ('N Ligne', 'n_ligne'),
            ('Cpt Comptable', 'cpt_comptable'),
            ('Date Fact', 'date_fact'),
            ('Date GL', 'date_gl')
        ]
        
        for file_col, _ in field_mappings:
            col = self._find_column(df, [file_col])
            if col:
                key_fields.append(col)
        
        if key_fields:
            duplicates = df.duplicated(subset=key_fields, keep=False)
            if duplicates.any():
                duplicate_rows = df[duplicates]
                issues_found.append(f"Found {len(duplicate_rows)} duplicate rows that should have been removed")
                logger.warning(f"⚠️ VALIDATION: {issues_found[-1]}")
                # Group duplicates to show which ones are duplicates
                duplicate_groups = df[duplicates].groupby(key_fields).size()
                logger.warning(f"   Found {len(duplicate_groups)} groups of duplicates")
                for (key_tuple, count) in duplicate_groups.head(5).items():
                    logger.warning(f"   Duplicate group ({count} rows): {dict(zip(key_fields, key_tuple))}")
        
        if not issues_found:
            logger.info("✅ VALIDATION: No filtering issues detected")
        else:
            logger.error(f"❌ VALIDATION FAILED: {len(issues_found)} issue(s) found")

    def _remove_duplicate_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate rows based on key identifying fields"""
        if len(df) == 0:
            return df
        
        # Key fields that should uniquely identify a revenue journal entry
        key_fields = []
        field_mappings = [
            ('Org Name', 'org_name'),
            ('N Fact', 'n_fact'),
            ('Typ Fact', 'typ_fact'),
            ('N Ligne', 'n_ligne'),
            ('Cpt Comptable', 'cpt_comptable'),
            ('Date Fact', 'date_fact'),
            ('Date GL', 'date_gl')
        ]
        
        for file_col, _ in field_mappings:
            col = self._find_column(df, [file_col])
            if col:
                key_fields.append(col)
        
        if not key_fields:
            logger.warning("⚠️ Could not find key fields for duplicate detection, skipping deduplication")
            return df
        
        original = len(df)
        # Remove duplicates, keeping the first occurrence
        df = df.drop_duplicates(subset=key_fields, keep='first')
        filtered = original - len(df)
        
        if filtered > 0:
            logger.info(f"Removed {filtered} duplicate rows based on key fields: {key_fields}")
        
        return df

    def _clean_numeric_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean numeric fields by removing dots"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers

        numeric_fields = [
            ['Prix Uni', 'unit price'],
            ['Mnt Ht', 'amount excluding tax'],
            ['Mnt Tax', 'tax amount'],
            ['Mnt Ttc', 'amount including tax'],
            ['Chiffre Aff Exe Dzd', 'revenue dzd']
        ]

        for field_keywords in numeric_fields:
            col = self._find_column(df, field_keywords)
            if col:
                df = RevenueProcessingHelpers.clean_numeric_field(df, col)

        return df

    def _calculate_tva(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate TVA = Mnt Ttc / Mnt Ht"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers

        logger.info(f"📊 Starting TVA calculation for {len(df)} rows")

        mnt_ttc = self._find_column(df, ['Mnt Ttc', 'amount including tax'])
        mnt_ht = self._find_column(df, ['Mnt Ht', 'amount excluding tax'])

        if mnt_ttc and mnt_ht:
            logger.info(f"   ✅ Found Mnt Ttc column: '{mnt_ttc}'")
            logger.info(f"   ✅ Found Mnt Ht column: '{mnt_ht}'")

            # Log statistics before calculation
            ttc_non_null = df[mnt_ttc].notna().sum()
            ht_non_null = df[mnt_ht].notna().sum()
            logger.info(f"   📊 Before calculation:")
            logger.info(f"      - Mnt Ttc values (non-null): {ttc_non_null}/{len(df)}")
            logger.info(f"      - Mnt Ht values (non-null): {ht_non_null}/{len(df)}")

            # Sample values
            if ttc_non_null > 0:
                ttc_sample = df[df[mnt_ttc].notna()][mnt_ttc].head(5).tolist()
                logger.info(f"      - Sample Mnt Ttc values: {ttc_sample}")

            if ht_non_null > 0:
                ht_sample = df[df[mnt_ht].notna()][mnt_ht].head(5).tolist()
                logger.info(f"      - Sample Mnt Ht values: {ht_sample}")

            result_df = RevenueProcessingHelpers.calculate_tva(df, mnt_ttc, mnt_ht)

            # Log statistics after calculation
            tva_col = 'TVA'
            if tva_col in result_df.columns:
                tva_non_null = result_df[tva_col].notna().sum()
                logger.info(f"   📊 After calculation:")
                logger.info(f"      - TVA values (non-null): {tva_non_null}/{len(result_df)}")

                if tva_non_null > 0:
                    tva_sample = result_df[result_df[tva_col].notna()][tva_col].head(5).tolist()
                    logger.info(f"      - Sample TVA values: {tva_sample}")

                    # Count zero vs non-zero TVA
                    tva_zero_count = (result_df[tva_col] == 0.0).sum()
                    tva_nonzero_count = ((result_df[tva_col] != 0.0) & result_df[tva_col].notna()).sum()
                    logger.info(f"      - TVA = 0.00: {tva_zero_count} rows")
                    logger.info(f"      - TVA != 0.00: {tva_nonzero_count} rows")
                else:
                    logger.warning(f"      ⚠️ All TVA values are NULL!")
            else:
                logger.error(f"   ❌ TVA column was not created!")

            return result_df
        else:
            logger.warning(f"   ⚠️ Required columns not found! Mnt Ttc: {mnt_ttc}, Mnt Ht: {mnt_ht}")
            return df

    def _calculate_ca_ttc(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Chiffre Aff Exe Dzd TTC"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers

        logger.info(f"📊 Starting Chiffre Aff Exe Dzd TTC calculation for {len(df)} rows")

        ca_col = self._find_column(
            df, ['Chiffre Aff Exe Dzd', 'revenue dzd'])

        if ca_col:
            logger.info(f"   ✅ Found Chiffre Aff Exe Dzd column: '{ca_col}'")

            # Check if TVA column exists
            tva_col = 'TVA'
            if tva_col not in df.columns:
                logger.warning(f"   ⚠️ TVA column not found! Cannot calculate CA TTC")
                return df

            logger.info(f"   ✅ Found TVA column")

            # Log statistics before calculation
            ca_non_null = df[ca_col].notna().sum()
            tva_non_null = df[tva_col].notna().sum()
            logger.info(f"   📊 Before calculation:")
            logger.info(f"      - CA values (non-null): {ca_non_null}/{len(df)}")
            logger.info(f"      - TVA values (non-null): {tva_non_null}/{len(df)}")

            # Sample values
            if ca_non_null > 0:
                ca_sample = df[df[ca_col].notna()][ca_col].head(5).tolist()
                logger.info(f"      - Sample CA values: {ca_sample}")

            if tva_non_null > 0:
                tva_sample = df[df[tva_col].notna()][tva_col].head(5).tolist()
                logger.info(f"      - Sample TVA values: {tva_sample}")

            # Perform calculation
            result_df = RevenueProcessingHelpers.calculate_ca_ttc(df, ca_col)

            # Log statistics after calculation
            ca_ttc_col = 'Chiffre_Aff_Exe_Dzd_TTC'
            if ca_ttc_col in result_df.columns:
                ca_ttc_non_null = result_df[ca_ttc_col].notna().sum()
                logger.info(f"   📊 After calculation:")
                logger.info(f"      - CA TTC values (non-null): {ca_ttc_non_null}/{len(result_df)}")

                if ca_ttc_non_null > 0:
                    ca_ttc_sample = result_df[result_df[ca_ttc_col].notna()][ca_ttc_col].head(5).tolist()
                    logger.info(f"      - Sample CA TTC values: {ca_ttc_sample}")

                    # Calculate statistics
                    ca_ttc_sum = result_df[ca_ttc_col].sum()
                    ca_ttc_mean = result_df[ca_ttc_col].mean()
                    ca_ttc_min = result_df[ca_ttc_col].min()
                    ca_ttc_max = result_df[ca_ttc_col].max()

                    logger.info(f"      - CA TTC Sum: {ca_ttc_sum:,.2f}")
                    logger.info(f"      - CA TTC Mean: {ca_ttc_mean:,.2f}")
                    logger.info(f"      - CA TTC Min: {ca_ttc_min:,.2f}")
                    logger.info(f"      - CA TTC Max: {ca_ttc_max:,.2f}")
                else:
                    logger.warning(f"      ⚠️ All CA TTC values are NULL!")
            else:
                logger.error(f"   ❌ CA TTC column was not created!")

            return result_df
        else:
            logger.warning(f"   ⚠️ Chiffre Aff Exe Dzd column not found! Cannot calculate CA TTC")
            return df

    def _match_account_descriptions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Match with account descriptions"""
        # Load account descriptions from database if not cached
        if not self.account_descriptions:
            accounts = self.db.query(AccountDescription).all()
            self.account_descriptions = {
                acc.cpt_comptable.upper(): acc for acc in accounts
            }

        cpt_col = self._find_column(
            df, ['Cpt Comptable', 'compte comptable'])
        if cpt_col:
            df['Account_Description'] = df[cpt_col].apply(
                lambda x: self.account_descriptions.get(str(x).strip().upper())
            )

        return df

    def _match_revenue_objectives(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Match with revenue objectives (using monthly objectives table)

        NOTE: Stores full RevenueDOTCorporate objects for monthly access.
        Use obj.annual_objective for annual total or obj.get_month_objective(month_num) for monthly.
        """
        # Load objectives from database if not cached
        if not self.revenue_objectives:
            from datetime import datetime
            current_year = datetime.utcnow().year
            objectives = self.db.query(RevenueDOTCorporate).filter(
                RevenueDOTCorporate.year == current_year
            ).all()
            from services.revenue_processing_helpers import RevenueProcessingHelpers
            # Store full objects for monthly access (not just annual_objective)
            self.revenue_objectives = {
                RevenueProcessingHelpers.clean_org_name_for_matching(obj.dot_name): obj
                for obj in objectives
            }

        from services.revenue_processing_helpers import RevenueProcessingHelpers
        org_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_col:
            # Return annual_objective for legacy compatibility, but store full object in cache
            df['Objectif_CA'] = df[org_col].apply(
                lambda x: RevenueProcessingHelpers.match_revenue_objective(
                    x, self.revenue_objectives)
            )

        return df

    def _calculate_achievement_rate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate achievement rate"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers
        ca_col = self._find_column(
            df, ['Chiffre Aff Exe Dzd', 'revenue dzd'])
        if ca_col:
            return RevenueProcessingHelpers.calculate_achievement_rate(df, ca_col)
        return df

    def _generate_export_files(self, df: pd.DataFrame, file_upload_id: int = None) -> Dict[str, Any]:
        """
        RÈGLE 18: Générer deux fichiers d'exportation
        1. Chiffre d'Affaires AR DOT (données normales)
        2. Anomalie Chiffre d'Affaires AR DOT (Cpt Comptable contenant A)
        """
        try:
            from datetime import datetime
            import os
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = "fastapi_backend/output/"
            os.makedirs(export_dir, exist_ok=True)
            
            # File 1: Chiffre d'Affaires AR DOT (normal data)
            normal_file = f"{export_dir}Chiffre_Affaires_AR_DOT_{timestamp}.xlsx"
            df_export = df.copy()
            
            # Format monetary columns with proper formatting
            monetary_cols = ['Prix Uni', 'Mnt Ht', 'Mnt Tax', 'Mnt Ttc', 'Chiffre Aff Exe Dzd']
            for col in monetary_cols:
                if col in df_export.columns:
                    # Convert to numeric and format with 2 decimal places
                    df_export[col] = pd.to_numeric(df_export[col], errors='coerce').round(2)
            
            # Add calculated columns if not present
            if 'TVA' not in df_export.columns:
                mnt_ttc_col = self._find_column(df_export, ['Mnt Ttc'])
                mnt_ht_col = self._find_column(df_export, ['Mnt Ht'])
                if mnt_ttc_col and mnt_ht_col:
                    df_export['TVA'] = df_export.apply(
                        lambda row: (row[mnt_ttc_col] / row[mnt_ht_col] if row[mnt_ht_col] and row[mnt_ht_col] != 0 else 0), 
                        axis=1
                    ).round(4)
            
            if 'Chiffre Aff Exe Dzd TTC' not in df_export.columns:
                ca_col = self._find_column(df_export, ['Chiffre Aff Exe Dzd'])
                if ca_col and 'TVA' in df_export.columns:
                    df_export['Chiffre Aff Exe Dzd TTC'] = (df_export[ca_col] * df_export['TVA']).round(2)
            
            # Save normal data file
            with pd.ExcelWriter(normal_file, engine='openpyxl') as writer:
                df_export.to_excel(writer, sheet_name='Chiffre Affaires AR DOT', index=False)
            
            logger.info(f"✅ Generated normal export file: {normal_file} ({len(df_export)} rows)")
            
            # File 2: Anomalie Chiffre d'Affaires AR DOT (anomalies)
            anomaly_file = f"{export_dir}Anomalie_Chiffre_Affaires_AR_DOT_{timestamp}.xlsx"
            
            # Create anomalies DataFrame from detected anomalies
            # Include ALL columns from the original row data
            anomalies_data = []
            for anomaly in self.anomalies:
                # Start with full row data if available
                row_data = anomaly.get('full_row_data', {})
                
                # Build record with all columns, starting with full row data
                record = dict(row_data) if row_data else {}
                
                # Add/override with anomaly-specific fields
                record['Type Anomalie'] = anomaly.get('type', 'Chiffre d\'Affaires AR DOT')
                record['Raison Anomalie'] = anomaly.get('reason', 'N/A')
                record['Date Detection'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Ensure key fields are present (use anomaly data if not in row_data)
                if 'Org Name' not in record or not record['Org Name']:
                    record['Org Name'] = anomaly.get('org_name', 'N/A')
                if 'N Fact' not in record or not record['N Fact']:
                    record['N Fact'] = anomaly.get('n_fact', 'N/A')
                if 'Cpt Comptable' not in record or not record['Cpt Comptable']:
                    record['Cpt Comptable'] = anomaly.get('cpt_comptable', 'N/A')
                if 'Description (ligne de produit)' not in record or not record.get('Description (ligne de produit)'):
                    record['Description (ligne de produit)'] = anomaly.get('description', 'N/A')
                
                anomalies_data.append(record)
            
            df_anomalies = pd.DataFrame(anomalies_data)
            
            # Save anomalies file
            with pd.ExcelWriter(anomaly_file, engine='openpyxl') as writer:
                df_anomalies.to_excel(writer, sheet_name='Anomalies CA AR DOT', index=False)
            
            logger.info(f"✅ Generated anomaly export file: {anomaly_file} ({len(df_anomalies)} rows)")
            
            # Save anomalies to database as well
            if file_upload_id and anomalies_data:
                self._save_anomalies_to_database(anomalies_data, file_upload_id)
            
            return {
                "success": True,
                "normal_file": normal_file,
                "anomaly_file": anomaly_file,
                "normal_rows": len(df_export),
                "anomaly_rows": len(df_anomalies),
                "export_directory": export_dir
            }
            
        except Exception as e:
            logger.error(f"Error generating export files: {e}")
            return {
                "success": False,
                "error": str(e),
                "normal_file": None,
                "anomaly_file": None
            }
    
    def _save_anomalies_to_database(self, anomalies_data: List[Dict], file_upload_id: int):
        """Save anomalies to RevenueAnomaly table"""
        try:
            import json
            for anomaly_data in anomalies_data:
                # Extract key fields (handle both 'Org Name' and 'DOT (Org Name)' formats)
                org_name = anomaly_data.get('Org Name') or anomaly_data.get('DOT (Org Name)', '')
                n_fact = anomaly_data.get('N Fact', '')
                cpt_comptable = anomaly_data.get('Cpt Comptable', '')
                description = anomaly_data.get('Description (ligne de produit)') or anomaly_data.get('Description', '')
                
                # Store full row data as JSON (excluding anomaly-specific fields that we'll add separately)
                original_data_dict = {k: v for k, v in anomaly_data.items() 
                                     if k not in ['Type Anomalie', 'Raison Anomalie', 'Date Detection', 'Date Détection']}
                
                revenue_anomaly = RevenueAnomaly(
                    file_upload_id=file_upload_id,
                    org_name=org_name,
                    n_fact=n_fact,
                    cpt_comptable=cpt_comptable,
                    description_ligne_de_produit=description,
                    anomaly_type=anomaly_data.get('Type Anomalie', "Chiffre d'Affaires AR DOT"),
                    anomaly_reason=anomaly_data.get('Raison Anomalie', ''),
                    original_data=json.dumps(original_data_dict, default=str, ensure_ascii=False)  # Store full data as JSON string
                )
                self.db.add(revenue_anomaly)
            
            self.db.flush()
            logger.info(f"✅ Saved {len(anomalies_data)} anomalies to database")
            
        except Exception as e:
            logger.error(f"Error saving anomalies to database: {e}")

    def _process_account_descriptions_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process account descriptions data"""
        logger.info(f"📋 Processing account descriptions data: {len(df)} rows")
        logger.info(f"   Columns: {list(df.columns)}")
        
        # Find and validate cpt_comptable column
        cpt_col = self._find_column(
            df, ['Cpt Comptable', 'cpt_comptable', 'cpt comptable', 'account code'])
        if cpt_col:
            logger.info(f"✅ Found Cpt Comptable column: '{cpt_col}'")
            
            # Show original values
            logger.info(f"   First 5 original account codes: {df[cpt_col].head(5).tolist()}")
            
            # Remove rows with empty cpt_comptable
            before = len(df)
            df = df[df[cpt_col].notna() & (df[cpt_col] != '')]
            after = len(df)
            if before != after:
                logger.info(f"   Removed {before - after} rows with empty account codes")
            
            # Remove duplicates (keep last occurrence)
            before = len(df)
            df = df.drop_duplicates(subset=[cpt_col], keep='last')
            after = len(df)
            if before != after:
                logger.info(f"   Removed {before - after} duplicate account codes")
        else:
            logger.warning(f"⚠️ No Cpt Comptable column found in file. Available columns: {list(df.columns)}")
        
        logger.info(f"✅ After processing: {len(df)} valid rows")
        return df

    def _process_objectives_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process objectives data"""
        logger.info(f"📋 Processing objectives data: {len(df)} rows")
        logger.info(f"   Columns: {list(df.columns)}")
        
        # Clean DOT names - Normalize but keep original format
        # DON'T use clean_org_name_for_matching which is too aggressive (removes DOT_, uppercase only)
        # We want to keep the original format for database storage
        dot_col = self._find_column(df, ['DOT', 'dot name'])
        if dot_col:
            logger.info(f"✅ Found DOT column: '{dot_col}'")
            
            # Show original values
            logger.info(f"   First 5 original DOT names: {df[dot_col].head(5).tolist()}")
            
            # Normalize: strip whitespace, normalize multiple spaces to single space, remove separators
            def normalize_dot_name(x):
                if pd.isna(x):
                    return None
                # Convert to string, strip
                name = str(x).strip()
                # Remove DOT_ prefix
                import re
                name = re.sub(r'^DOT[_\s]+', '', name, flags=re.IGNORECASE)
                # Replace -, – and _ with spaces
                name = name.replace('-', ' ').replace('–', ' ').replace('_', ' ')
                # Replace multiple spaces/tabs with single space
                name = re.sub(r'\s+', ' ', name)
                return name.strip()
            
            df[dot_col] = df[dot_col].apply(normalize_dot_name)
            
            logger.info(f"   First 5 normalized DOT names: {df[dot_col].head(5).tolist()}")
            
            # Remove rows with empty DOT names
            before = len(df)
            df = df[df[dot_col].notna() & (df[dot_col] != '')]
            after = len(df)
            if before != after:
                logger.info(f"   Removed {before - after} rows with empty DOT names")
            
            # Remove duplicates (keep last occurrence)
            before = len(df)
            df = df.drop_duplicates(subset=[dot_col], keep='last')
            after = len(df)
            if before != after:
                logger.info(f"   Removed {before - after} duplicate DOT entries")
        else:
            logger.warning(f"⚠️ No DOT column found in file. Available columns: {list(df.columns)}")
            
        # Validate objectif_ca column
        objectif_col = self._find_column(df, ['Objectif C.A', 'objectif', 'objective', 'target'])
        if objectif_col:
            logger.info(f"✅ Found Objectif C.A column: '{objectif_col}'")
            # Remove rows with invalid objectif_ca
            before = len(df)
            df = df[df[objectif_col].notna()]
            after = len(df)
            if before != after:
                logger.info(f"   Removed {before - after} rows with empty objectif_ca")
        else:
            logger.warning(f"⚠️ No Objectif C.A column found. Available columns: {list(df.columns)}")
            
        logger.info(f"✅ After processing: {len(df)} valid rows")
        return df

    def _save_journal_to_database(self, records: List[Dict[str, Any]],
                                    file_upload_id: int = None,
                                    progress_callback=None) -> Dict[str, Any]:
        """Save revenue journal records to database"""
        try:
            from revenue_column_mapping import map_revenue_journal_record
            saved_count = 0
            errors = []
            
            logger.info(f"💾 Starting to save {len(records)} revenue journal records to database (file_upload_id={file_upload_id})")
            
            for i, record in enumerate(records):
                try:
                    mapped = map_revenue_journal_record(
                        record, file_upload_id)

                    # Get or create DOT for Chiffre d'Affaires module
                    if mapped.get('org_name'):
                        dot = self._get_or_create_dot(
                            mapped['org_name'],
                            f"DOT for {mapped['org_name']} organization"
                        )
                        mapped['dot_id'] = dot.id

                        # Match revenue objective by org_name (using monthly objectives table)
                        from datetime import datetime
                        current_year = datetime.utcnow().year
                        objective = self.db.query(RevenueDOTCorporate).filter(
                            RevenueDOTCorporate.dot_name.ilike(mapped['org_name']),
                            RevenueDOTCorporate.year == current_year
                        ).first()
                        if objective:
                            mapped['revenue_objective_id'] = objective.id
                            # Calculate achievement rate (CA / Monthly Objectif)
                            # Extract month from date_gl to get month-specific objective
                            if mapped.get('chiffre_aff_exe_dzd') and mapped.get('date_gl'):
                                try:
                                    ca = float(mapped['chiffre_aff_exe_dzd'])
                                    # Get month number from date_gl (1-12)
                                    date_gl = mapped['date_gl']
                                    if isinstance(date_gl, str):
                                        # Parse string date to datetime
                                        from dateutil import parser
                                        date_gl = parser.parse(date_gl)
                                    month_num = date_gl.month if hasattr(date_gl, 'month') else None

                                    if month_num:
                                        # Get month-specific objective
                                        monthly_objective = objective.get_month_objective(month_num)
                                        if monthly_objective and monthly_objective != 0:
                                            mapped['taux_realisation_ca'] = (ca / monthly_objective) * 100
                                            logger.debug(f"   📊 Achievement rate: {ca} / {monthly_objective} = {mapped['taux_realisation_ca']:.2f}%")
                                except (ValueError, TypeError, AttributeError) as e:
                                    logger.warning(f"   ⚠️ Error calculating monthly achievement rate: {e}")

                    # Extract account_description_id from matched Account_Description object
                    account_desc = record.get('Account_Description')
                    if account_desc and hasattr(account_desc, 'id'):
                        mapped['account_description_id'] = account_desc.id
                    elif account_desc is None:
                        # Try to match by cpt_comptable if Account_Description wasn't matched
                        if mapped.get('cpt_comptable'):
                            account = self.db.query(AccountDescription).filter(
                                AccountDescription.cpt_comptable == mapped['cpt_comptable']
                            ).first()
                            if account:
                                mapped['account_description_id'] = account.id

                    journal_entry = RevenueJournal(**mapped)
                    self.db.add(journal_entry)
                    saved_count += 1
                    
                    # Progress callback every 100 records
                    if progress_callback and (i + 1) % 100 == 0:
                        progress_callback({
                            "status": "saving",
                            "progress": int((i + 1) / len(records) * 100),
                            "message": f"Saving revenue journal: {i + 1}/{len(records)}"
                        })

                except Exception as e:
                    errors.append({"record": i, "error": str(e)})

            # Commit transaction
            try:
                # Check if there are any pending changes
                if self.db.new or self.db.dirty or self.db.deleted:
                    logger.info(f"🔄 Preparing to commit: {len(self.db.new)} new, {len(self.db.dirty)} dirty, {len(self.db.deleted)} deleted")
                else:
                    logger.warning(f"⚠️ No pending changes detected before commit! saved_count={saved_count}")
                
                self.db.flush()
                logger.info(f"🔄 Flushed session: {saved_count} records to save")
                
                self.db.commit()
                logger.info(f"✅ Transaction committed successfully")
                
                # Refresh session to ensure we can query
                self.db.expire_all()
                
                # Verify save by counting records in DB
                total_in_db = self.db.query(RevenueJournal).count()
                logger.info(f"📊 Total revenue journal entries in database after commit: {total_in_db}")
                
                # Verify save by checking count
                if file_upload_id:
                    saved_count_verify = self.db.query(RevenueJournal).filter(
                        RevenueJournal.file_upload_id == file_upload_id
                    ).count()
                    logger.info(f"✅ Verified {saved_count_verify} records saved for file_upload_id={file_upload_id}")
                else:
                    logger.warning(f"⚠️ No file_upload_id provided, cannot verify saved records")
                
            except Exception as commit_error:
                logger.error(f"❌ Error committing transaction: {commit_error}")
                logger.exception(commit_error)
                # Log more details about the error
                if hasattr(commit_error, 'orig'):
                    logger.error(f"   Original error: {commit_error.orig}")
                if hasattr(commit_error, 'statement'):
                    logger.error(f"   SQL Statement: {commit_error.statement}")
                self.db.rollback()
                raise
            
            return {
                "success": True,
                "saved_count": saved_count,
                "errors": errors
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving to database: {e}")
            return {
                "success": False,
                "error": str(e),
                "saved_count": 0
            }

    def _find_column(self, df: pd.DataFrame, keywords: list) -> Optional[str]:
        """Find column by keywords"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers
        return RevenueProcessingHelpers._find_column(df, keywords)

    def _generate_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate statistics for revenue data"""
        stats = {
            "total_records": len(df),
            "by_org_name": {},
            "by_month": {},
            "total_revenue": 0.0
        }

        # By Org Name
        org_col = self._find_column(df, ['Org Name', 'organisation'])
        ca_col = self._find_column(
            df, ['Chiffre Aff Exe Dzd', 'revenue dzd'])

        if org_col and ca_col:
            org_stats = df.groupby(org_col)[ca_col].sum()
            stats["by_org_name"] = org_stats.to_dict()
            stats["total_revenue"] = float(df[ca_col].sum())

        # By Month
        date_col = self._find_column(df, ['Date GL', 'gl date'])
        if date_col and ca_col:
            df_temp = df.copy()
            df_temp[date_col] = pd.to_datetime(
                df_temp[date_col], errors='coerce')
            df_temp['Month'] = df_temp[date_col].dt.to_period('M')
            month_stats = df_temp.groupby('Month')[ca_col].sum()
            stats["by_month"] = {str(k): float(v)
                                  for k, v in month_stats.to_dict().items()}

        return stats

    def _generate_pivot_tables(self, file_upload_id: int = None) -> Dict[str, Any]:
        """
        RÈGLE 18: Generate TCD (Tableau Croisé Dynamique)
        Creates pre-calculated pivot tables for fast dashboard queries
        """
        try:
            from services.revenue_pivot_service import RevenuePivotService

            logger.info("📊 RÈGLE 18: Génération des TCD (Tableaux Croisés Dynamiques)...")

            pivot_service = RevenuePivotService(self.db)
            result = pivot_service.generate_all_pivots(file_upload_id)

            logger.info(f"✅ TCD générés avec succès: {sum(result.values())} enregistrements")

            return {
                "success": True,
                "pivot_counts": result,
                "total_pivots": sum(result.values())
            }

        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération des TCD: {e}")
            return {
                "success": False,
                "error": str(e),
                "pivot_counts": {}
            }

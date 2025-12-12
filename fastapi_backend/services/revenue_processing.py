"""
Revenue (Chiffre d'Affaires AR DOT) Processing Service
Handles data filtering, transformation, and validation for revenue files
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import logging
from sqlalchemy.orm import Session
from models.revenue import RevenueJournal, AccountDescription, RevenueObjective, RevenueAnomaly
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
        dot = DOTService.get_or_create_dot(
            db=self.db,
            name=name,
            description=description,
            module=MODULE_CHIFFRE_AFFAIRES
        )
        logger.info(
            f"✅ DOT '{name}' → ID: {dot.id}, Module: '{MODULE_CHIFFRE_AFFAIRES}', "
            f"DB Name: '{dot.name}'"
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
            # Log Taux Change column before converting to dict
            taux_change_col = self._find_column(df_processed, ['Taux Change', 'taux change', 'taux_change', 'TauxChange', 'Exchange Rate'])
            if taux_change_col:
                logger.info(f"📊 Found 'Taux Change' column: '{taux_change_col}'")
                non_null_count = df_processed[taux_change_col].notna().sum()
                logger.info(f"📊 Taux Change non-null values in processed DataFrame: {non_null_count}/{len(df_processed)}")
                if non_null_count > 0:
                    sample_values = df_processed[df_processed[taux_change_col].notna()][taux_change_col].head(10).tolist()
                    logger.info(f"📊 Sample Taux Change values from DataFrame: {sample_values}")
                else:
                    logger.warning(f"⚠️ All Taux Change values are NaN in processed DataFrame!")
            else:
                logger.warning(f"⚠️ 'Taux Change' column not found in processed DataFrame!")
                logger.info(f"   Available columns: {list(df_processed.columns)}")
            
            processed_data = df_processed.to_dict('records')
            
            # Log Taux Change values after converting to dict
            if taux_change_col:
                taux_in_dict = [r.get(taux_change_col) for r in processed_data[:100] if taux_change_col in r and r.get(taux_change_col) is not None and not pd.isna(r.get(taux_change_col))]
                logger.info(f"📊 Taux Change values in dict (first 100 records): {len(taux_in_dict)} non-null values found")
                if taux_in_dict:
                    logger.info(f"📊 Sample Taux Change values from dict: {taux_in_dict[:10]}")
            
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
        """Process Revenue Objectives file (Objectif C.A.xlsx)"""
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

    def _read_file(self, file_path: str) -> pd.DataFrame:
        """Read CSV or Excel file, with support for HTML files masquerading as .xls"""
        from pathlib import Path
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.csv':
            return pd.read_csv(file_path, low_memory=False)
        elif file_ext == '.xlsx':
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

        # 1. Garder que le tableau (keep only table data - skip if needed)

        # 1a. CROSS-REFERENCING FIRST: Matcher avec Description Cpt Comptable
        df = self._match_account_descriptions(df)
        logger.info(f"Matched account descriptions")

        # 1b. CROSS-REFERENCING FIRST: Matcher avec Objectif C.A
        df = self._match_revenue_objectives(df)
        logger.info(f"Matched revenue objectives")

        # 2. Org Name: Supprimer toutes les lignes contenant AT_SIEGE
        df = self._filter_at_siege(df)
        logger.info(f"After AT_SIEGE filter: {len(df)} rows")

        # 3. Org Name: Remplacer DOT_ par vide
        df = self._clean_org_name_dot(df)

        # 4. Org Name: Remplacer – et _ par espace
        df = self._clean_org_name_separators(df)

        # 5. Trier par Org Name, Type Fact et N Fact
        df = self._sort_by_org_type_invoice(df)
        logger.info(f"Sorted by Org Name, Type Fact, N Fact")

        # 6. Clean numeric fields (MOVED UP - before anomaly detection)
        df = self._clean_numeric_fields(df)
        logger.info(f"Cleaned numeric fields")

        # 7. Calculate TVA (MOVED UP - before anomaly detection)
        df = self._calculate_tva(df)
        logger.info(f"Calculated TVA column")

        # 8. Calculate Chiffre Aff Exe Dzd TTC (MOVED UP - before anomaly detection)
        df = self._calculate_ca_ttc(df)
        logger.info(f"Calculated CA TTC column")

        # 9. Skip individual achievement rate calculation (not meaningful for individual entries)
        # Achievement rate should only be calculated at aggregate levels (by DOT, by Month, etc.)
        # Individual invoice lines should not have achievement rates
        # df = self._calculate_achievement_rate(df)  # REMOVED - meaningless for individual lines
        logger.info(f"Skipped individual achievement rate calculation (will be calculated at aggregate level only)")

        # 10. Detect anomalies (NOW CAPTURES ALL 35+ COLUMNS INCLUDING CALCULATED ONES)
        # Si Cpt Comptable contenant la lettre A => marquer comme Anomalie
        df = self._detect_anomalies(df)
        logger.info(f"Detected {len(self.anomalies)} anomalies with ALL columns including calculated fields")

        # 11. Filter out anomalies (remove rows with 'A' in Cpt Comptable)
        df = self._filter_cpt_comptable_with_a(df)
        logger.info(f"After Cpt Comptable filter: {len(df)} rows")

        # 12. Keep most recent year
        df = self._keep_most_recent_year(df)
        logger.info(f"After keeping most recent year: {len(df)} rows")

        self.filtered_count = original_count - len(df)
        logger.info(
            f"Processing complete: {len(df)} rows remaining, {self.filtered_count} filtered")

        return df

    def _filter_at_siege(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows where Org Name contains 'AT_SIEGE'"""
        org_name_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_name_col:
            original = len(df)
            df = df[~df[org_name_col].astype(
                str).str.contains('AT_SIEGE', case=False, na=False)]
            filtered = original - len(df)
            if filtered > 0:
                logger.info(f"Filtered {filtered} rows containing AT_SIEGE")
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
        """Replace – and _ with spaces in Org Name"""
        org_name_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_name_col:
            df.loc[:, org_name_col] = df[org_name_col].astype(str).str.replace(
                '–', ' ').str.replace('_', ' ').str.replace('  ', ' ').str.strip()
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
                # Store complete original row data with all columns
                original_row_data = {}
                for col in df.columns:
                    value = row.get(col)
                    # Convert pandas types to Python native types for JSON serialization
                    if pd.isna(value):
                        original_row_data[col] = None
                    elif isinstance(value, pd.Timestamp):
                        original_row_data[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, complex)):
                        # Convert numpy/pandas numeric types to Python float
                        original_row_data[col] = float(value) if pd.notna(value) else None
                    else:
                        # Keep as-is for strings and other types
                        original_row_data[col] = value
                
                self.anomalies.append({
                    "type": "Chiffre d'Affaires AR DOT",
                    "reason": anomaly_reason,
                    "original_row": original_row_data  # Store complete row with all columns
                })
                anomaly_rows.append(idx)

        return df

    def _filter_cpt_comptable_with_a(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows where Cpt Comptable contains letter 'A'"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers
        cpt_col = self._find_column(
            df, ['Cpt Comptable', 'compte comptable'])
        if cpt_col:
            return RevenueProcessingHelpers.filter_cpt_comptable_with_a(df, cpt_col)
        return df

    def _keep_most_recent_year(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only most recent year in Date GL"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers
        date_col = self._find_column(df, ['Date GL', 'gl date'])
        if date_col:
            return RevenueProcessingHelpers.keep_most_recent_year(df, date_col)
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
        """Match with revenue objectives"""
        # Load objectives from database if not cached
        if not self.revenue_objectives:
            objectives = self.db.query(RevenueObjective).all()
            from services.revenue_processing_helpers import RevenueProcessingHelpers
            self.revenue_objectives = {
                RevenueProcessingHelpers.clean_org_name_for_matching(obj.dot_name): obj.objectif_ca
                for obj in objectives
            }

        from services.revenue_processing_helpers import RevenueProcessingHelpers
        org_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_col:
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
            
            # Create anomalies DataFrame with ALL original columns from the original file
            anomalies_data = []
            for anomaly in self.anomalies:
                original_row = anomaly.get('original_row', {})
                
                # Start with all original row data
                anomaly_record = original_row.copy()
                
                # Add anomaly-specific fields
                anomaly_record['Type Anomalie'] = anomaly.get('type', 'Chiffre d\'Affaires AR DOT')
                anomaly_record['Raison Anomalie'] = anomaly.get('reason', 'N/A')
                anomaly_record['Date Detection'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                anomalies_data.append(anomaly_record)
            
            # Create DataFrame from anomalies
            if anomalies_data:
                df_anomalies = pd.DataFrame(anomalies_data)
                # Ensure consistent column order: original columns first, then anomaly fields
                original_cols = [col for col in df.columns if col not in ['Type Anomalie', 'Raison Anomalie', 'Date Detection']]
                anomaly_cols = ['Type Anomalie', 'Raison Anomalie', 'Date Detection']
                # Reorder columns: original columns first, then anomaly-specific columns
                all_cols = original_cols + [col for col in anomaly_cols if col in df_anomalies.columns]
                df_anomalies = df_anomalies[[col for col in all_cols if col in df_anomalies.columns]]
            else:
                df_anomalies = pd.DataFrame()
            
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
                # Extract key fields from original row data
                org_name_col = self._find_column(
                    pd.DataFrame([anomaly_data]), ['Org Name', 'organisation'])
                n_fact_col = self._find_column(
                    pd.DataFrame([anomaly_data]), ['N Fact', 'invoice'])
                cpt_col = self._find_column(
                    pd.DataFrame([anomaly_data]), ['Cpt Comptable', 'compte comptable'])
                desc_col = self._find_column(
                    pd.DataFrame([anomaly_data]), ['Description (ligne de produit)', 'description ligne'])
                
                revenue_anomaly = RevenueAnomaly(
                    file_upload_id=file_upload_id,
                    org_name=anomaly_data.get(org_name_col) if org_name_col else anomaly_data.get('Org Name'),
                    n_fact=anomaly_data.get(n_fact_col) if n_fact_col else anomaly_data.get('N Fact'),
                    cpt_comptable=anomaly_data.get(cpt_col) if cpt_col else anomaly_data.get('Cpt Comptable'),
                    description_ligne_de_produit=anomaly_data.get(desc_col) if desc_col else anomaly_data.get('Description (ligne de produit)'),
                    anomaly_type=anomaly_data.get('Type Anomalie', "Chiffre d'Affaires AR DOT"),
                    anomaly_reason=anomaly_data.get('Raison Anomalie'),
                    original_data=json.dumps(anomaly_data, default=str, ensure_ascii=False)  # Store full data as JSON
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
            
            # Normalize: strip whitespace, normalize multiple spaces to single space
            def normalize_dot_name(x):
                if pd.isna(x):
                    return None
                # Convert to string, strip, normalize spaces
                name = str(x).strip()
                # Replace multiple spaces/tabs with single space
                import re
                name = re.sub(r'\s+', ' ', name)
                return name
            
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
            if records:
                logger.info(f"   📊 First record sample keys: {list(records[0].keys())[:20]}")
            
            # Log all Taux Change values from the file
            taux_change_values = []
            taux_change_column_names = ['Taux Change', 'Taux Change', 'taux_change', 'taux change', 'TauxChange', 'Exchange Rate', 'exchange rate']
            for i, record in enumerate(records):
                for col_name in taux_change_column_names:
                    if col_name in record:
                        value = record[col_name]
                        if not pd.isna(value) and value is not None and str(value).strip() not in ['', 'nan', 'None', 'null']:
                            taux_change_values.append((i+1, col_name, value, type(value).__name__))
                        break
            
            if taux_change_values:
                logger.info(f"📊 Found {len(taux_change_values)} records with Taux Change values:")
                for idx, (row_num, col_name, val, val_type) in enumerate(taux_change_values[:50]):  # Log first 50
                    logger.info(f"   Row {row_num}: '{col_name}' = {val} (type: {val_type})")
                if len(taux_change_values) > 50:
                    logger.info(f"   ... and {len(taux_change_values) - 50} more records with Taux Change values")
            else:
                logger.warning(f"⚠️ No Taux Change values found in any of the {len(records)} records!")
                # Log what columns are actually available
                if records:
                    available_cols = [k for k in records[0].keys() if 'taux' in k.lower() or 'change' in k.lower() or 'rate' in k.lower() or 'exchange' in k.lower()]
                    logger.info(f"   Available columns containing 'taux', 'change', 'rate', or 'exchange': {available_cols}")
                    # Also check first few records for any column that might be Taux Change
                    logger.info(f"   All columns in first record: {list(records[0].keys())}")
            
            for i, record in enumerate(records):
                try:
                    # Log original record data for first few records
                    if i < 5:
                        logger.info(f"📋 Processing record {i+1}/{len(records)}")
                        logger.info(f"   Raw record keys: {list(record.keys())[:15]}")
                        # Log critical fields from raw record
                        for key in ['Date Fact', 'Date facture GL', 'Date GL', 'Periode de facturation', 
                                   'Taux Change', 'Memo Line Id', 'Cpt Comptable']:
                            if key in record:
                                raw_val = record[key]
                                # Check if it's NaN
                                if pd.isna(raw_val):
                                    logger.info(f"   {key}: NaN/empty (type: {type(raw_val).__name__})")
                                else:
                                    logger.info(f"   {key}: {raw_val} (type: {type(raw_val).__name__})")
                    
                    mapped = map_revenue_journal_record(
                        record, file_upload_id)

                    # Log mapped values for first few records
                    if i < 5:
                        logger.info(f"   ✅ Mapped values for record {i+1}:")
                        date_fields = ['date_fact', 'date_facture_gl', 'date_gl']
                        other_fields = ['periode_de_facturation', 'taux_change', 'memo_line_id', 'account_description_id']
                        for field in date_fields + other_fields:
                            value = mapped.get(field)
                            status = "✅" if value is not None else "❌ MISSING"
                            logger.info(f"      {status} {field}: {value}")

                    # Get or create DOT for Chiffre d'Affaires module
                    if mapped.get('org_name'):
                        dot = self._get_or_create_dot(
                            mapped['org_name'],
                            f"DOT for {mapped['org_name']} organization"
                        )
                        mapped['dot_id'] = dot.id

                        # Match revenue objective by org_name
                        objective = self.db.query(RevenueObjective).filter(
                            RevenueObjective.dot_name.ilike(mapped['org_name'])
                        ).first()
                        if objective:
                            mapped['revenue_objective_id'] = objective.id
                            # Calculate achievement rate (CA / Objectif)
                            if mapped.get('chiffre_aff_exe_dzd') and objective.objectif_ca:
                                try:
                                    ca = float(mapped['chiffre_aff_exe_dzd'])
                                    objectif = float(objective.objectif_ca)
                                    if objectif != 0:
                                        mapped['taux_realisation_ca'] = (ca / objectif) * 100
                                except (ValueError, TypeError):
                                    pass

                    # Extract account_description_id from matched Account_Description object
                    account_desc = record.get('Account_Description')
                    if account_desc and hasattr(account_desc, 'id'):
                        mapped['account_description_id'] = account_desc.id
                        if i < 5:
                            logger.info(f"   ✅ Matched AccountDescription ID: {account_desc.id} from Account_Description object")
                    elif account_desc is None:
                        # Try to match by cpt_comptable if Account_Description wasn't matched
                        if mapped.get('cpt_comptable'):
                            account = self.db.query(AccountDescription).filter(
                                AccountDescription.cpt_comptable == mapped['cpt_comptable']
                            ).first()
                            if account:
                                mapped['account_description_id'] = account.id
                                if i < 5:
                                    logger.info(f"   ✅ Matched AccountDescription ID: {account.id} by cpt_comptable query")
                            else:
                                if i < 5:
                                    logger.warning(f"   ⚠️ No AccountDescription found for cpt_comptable: {mapped.get('cpt_comptable')}")

                    # Log missing fields for debugging
                    missing_fields = []
                    for field in ['date_fact', 'date_facture_gl', 'date_gl', 'periode_de_facturation', 'taux_change', 'memo_line_id', 'account_description_id']:
                        if field not in mapped or mapped[field] is None:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        if i < 5:
                            logger.warning(f"   ⚠️ Record {i+1} missing fields: {missing_fields}")
                        else:
                            # Log periodically for records beyond first 5
                            if i % 100 == 0:
                                logger.warning(f"   ⚠️ Record {i+1} missing fields: {missing_fields}")

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
                
                # Verify objects are still in session before commit
                pending_count = len([obj for obj in self.db.new if isinstance(obj, RevenueJournal)])
                logger.info(f"📊 RevenueJournal objects pending in session: {pending_count}")
                
                if pending_count == 0 and saved_count > 0:
                    logger.error(f"❌ CRITICAL: No RevenueJournal objects in session but saved_count={saved_count}! This indicates objects were lost.")
                
                self.db.commit()
                logger.info(f"✅ Transaction committed successfully")
                
                # Refresh session to ensure we can query
                self.db.expire_all()
                
                # Verify save by counting records in DB
                total_in_db = self.db.query(RevenueJournal).count()
                logger.info(f"📊 Total revenue journal entries in database after commit: {total_in_db}")
                
                # Show journal entries from the file we just processed with detailed field logging
                if file_upload_id:
                    recent_journals = self.db.query(RevenueJournal).filter(
                        RevenueJournal.file_upload_id == file_upload_id
                    ).limit(5).all()
                    logger.info(f"📋 Sample journal entries saved (file_upload_id={file_upload_id}): {len(recent_journals)} found")
                    
                    # Count records with taux_change values
                    taux_change_count = self.db.query(RevenueJournal).filter(
                        RevenueJournal.file_upload_id == file_upload_id,
                        RevenueJournal.taux_change.isnot(None)
                    ).count()
                    logger.info(f"📊 Taux Change statistics: {taux_change_count}/{saved_count} records have taux_change values")
                    
                    for journal in recent_journals:
                        logger.info(f"   ✅ ID={journal.id}, org_name='{journal.org_name}', n_fact='{journal.n_fact}'")
                        logger.info(f"      📅 Dates - date_fact={journal.date_fact}, date_facture_gl={journal.date_facture_gl}, date_gl={journal.date_gl}")
                        logger.info(f"      📝 Other - periode_de_facturation='{journal.periode_de_facturation}', taux_change={journal.taux_change}, memo_line_id='{journal.memo_line_id}'")
                        logger.info(f"      🔗 Relationships - account_description_id={journal.account_description_id}, revenue_objective_id={journal.revenue_objective_id}")
                        logger.info(f"      💰 Financial - cpt_comptable='{journal.cpt_comptable}', chiffre_aff_exe_dzd={journal.chiffre_aff_exe_dzd}, mnt_ht={journal.mnt_ht}, mnt_ttc={journal.mnt_ttc}")
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

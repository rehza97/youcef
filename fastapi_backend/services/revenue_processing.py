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

            return {
                "success": True,
                "original_rows": len(df),
                "processed_rows": len(df_processed),
                "filtered_rows": len(df) - len(df_processed),
                "anomalies": self.anomalies,
                "statistics": stats,
                "database_save": save_result
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

                # Get or create DOT
                dot = DOTService.get_or_create_dot(
                    self.db, mapped['dot_name'])
                mapped['dot_id'] = dot.id
                logger.info(f"🔍 DOT '{mapped['dot_name']}' → DOT ID: {dot.id}, DOT name in DB: '{dot.name}'")

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
                    # Read HTML tables without header first to detect structure
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
                    
                    logger.info(f"📊 Using HTML table {best_table_idx} with {len(best_table.columns)} columns and {len(best_table)} rows")
                    
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

        # 6. Si Cpt Comptable contenant la lettre A et Description ne commence pas par @
        #    => mettre comme Anomalie
        df = self._detect_anomalies(df)
        logger.info(f"Detected {len(self.anomalies)} anomalies")

        # 7. Cpt Comptable : Supprimer toutes les lignes contenant la lettre A
        df = self._filter_cpt_comptable_with_a(df)
        logger.info(f"After Cpt Comptable filter: {len(df)} rows")

        # 8. Date GL : Garder les lignes ayant l'année la plus récente
        df = self._keep_most_recent_year(df)
        logger.info(f"After keeping most recent year: {len(df)} rows")

        # 9-13. Clean numeric fields (remove ".")
        df = self._clean_numeric_fields(df)

        # 14. Mettre le séparateur de millier avec deux chiffres après la virgule
        # (This is for display/export, not for processing)

        # 15. Ajouter une colonne TVA (=Mnt Ttc/Mnt Ht)
        df = self._calculate_tva(df)

        # 16. Ajouter une colonne Chiffre Aff Exe Dzd TTC (=Chiffre Aff Exe Dzd * TVA)
        df = self._calculate_ca_ttc(df)

        # 17. Matcher avec Description Cpt Comptable
        df = self._match_account_descriptions(df)

        # 18. Matcher avec Objectif C.A
        df = self._match_revenue_objectives(df)

        # 19. Ajouter une colonne Taux de réalisation C.A
        df = self._calculate_achievement_rate(df)

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
        """Remove 'DOT_' prefix from Org Name"""
        org_name_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_name_col:
            df.loc[:, org_name_col] = df[org_name_col].astype(
                str).str.replace('DOT_', '', case=False)
        return df

    def _clean_org_name_separators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Replace – and _ with spaces in Org Name"""
        org_name_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_name_col:
            df.loc[:, org_name_col] = df[org_name_col].astype(str).str.replace(
                '–', ' ').str.replace('_', ' ').str.replace('  ', ' ').str.strip()
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
                self.anomalies.append({
                    "type": "Chiffre d'Affaires AR DOT",
                    "org_name": row.get(self._find_column(df, ['Org Name', 'organisation']), 'N/A'),
                    "n_fact": row.get(self._find_column(df, ['N Fact', 'invoice']), 'N/A'),
                    "reason": anomaly_reason,
                    "cpt_comptable": row.get(cpt_col, 'N/A'),
                    "description": row.get(desc_col, 'N/A')
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
        mnt_ttc = self._find_column(df, ['Mnt Ttc', 'amount including tax'])
        mnt_ht = self._find_column(df, ['Mnt Ht', 'amount excluding tax'])
        if mnt_ttc and mnt_ht:
            return RevenueProcessingHelpers.calculate_tva(df, mnt_ttc, mnt_ht)
        return df

    def _calculate_ca_ttc(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Chiffre Aff Exe Dzd TTC"""
        from services.revenue_processing_helpers import RevenueProcessingHelpers
        ca_col = self._find_column(
            df, ['Chiffre Aff Exe Dzd', 'revenue dzd'])
        if ca_col:
            return RevenueProcessingHelpers.calculate_ca_ttc(df, ca_col)
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

            for i, record in enumerate(records):
                try:
                    mapped = map_revenue_journal_record(
                        record, file_upload_id)

                    # Get or create DOT
                    if mapped.get('org_name'):
                        dot = DOTService.get_or_create_dot(
                            self.db, mapped['org_name'])
                        mapped['dot_id'] = dot.id

                    journal_entry = RevenueJournal(**mapped)
                    self.db.add(journal_entry)
                    saved_count += 1

                    if progress_callback and i % 100 == 0:
                        progress_callback({
                            "status": "saving",
                            "progress": int((i + 1) / len(records) * 100),
                            "message": f"Saving revenue journal: {i + 1}/{len(records)}"
                        })

                except Exception as e:
                    errors.append({"record": i, "error": str(e)})

            # Commit transaction
            try:
                self.db.flush()
                logger.info(f"🔄 Flushed session: {saved_count} records to save")
                
                self.db.commit()
                logger.info(f"✅ Transaction committed successfully")
                
                # Verify save by counting records in DB
                total_in_db = self.db.query(RevenueJournal).count()
                logger.info(f"📊 Total revenue journal entries in database after commit: {total_in_db}")
                
                # Show journal entries from the file we just processed
                if file_upload_id:
                    recent_journals = self.db.query(RevenueJournal).filter(
                        RevenueJournal.file_upload_id == file_upload_id
                    ).limit(5).all()
                    logger.info(f"📋 Found {len(recent_journals)} journal entries with file_upload_id={file_upload_id}:")
                    for journal in recent_journals:
                        logger.info(f"   ✅ ID={journal.id}, org_name='{journal.org_name}', n_fact='{journal.n_fact}', cpt_comptable='{journal.cpt_comptable}', chiffre_aff_exe_dzd={journal.chiffre_aff_exe_dzd}")
                        logger.debug(f"      All fields: origine='{journal.origine}', typ_fact='{journal.typ_fact}', client='{journal.client}', mnt_ht={journal.mnt_ht}, mnt_ttc={journal.mnt_ttc}")
                
            except Exception as commit_error:
                logger.error(f"❌ Error committing transaction: {commit_error}")
                logger.exception(commit_error)
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

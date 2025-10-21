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
            logger.info(
                f"Loaded {len(df)} account descriptions from file")

            # Clean and validate
            df_processed = self._process_account_descriptions_data(df)

            # Save to database
            records = df_processed.to_dict('records')
            saved_count = 0

            for record in records:
                from revenue_column_mapping import map_account_description_record
                mapped = map_account_description_record(
                    record, file_upload_id)

                if not mapped.get('cpt_comptable'):
                    continue

                # Check if exists
                existing = self.db.query(AccountDescription).filter(
                    AccountDescription.cpt_comptable == mapped['cpt_comptable']
                ).first()

                if existing:
                    # Update
                    for key, value in mapped.items():
                        if key != 'created_at' and hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create
                    account_desc = AccountDescription(**mapped)
                    self.db.add(account_desc)

                saved_count += 1

            self.db.commit()

            return {
                "success": True,
                "processed_rows": len(df_processed),
                "saved_count": saved_count
            }

        except Exception as e:
            logger.error(f"Error processing account descriptions: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def process_revenue_objectives(self, file_path: str, file_upload_id: int = None) -> Dict[str, Any]:
        """Process Revenue Objectives file (Objectif C.A.xlsx)"""
        try:
            df = self._read_file(file_path)
            logger.info(f"Loaded {len(df)} revenue objectives from file")

            # Clean and validate
            df_processed = self._process_objectives_data(df)

            # Save to database
            records = df_processed.to_dict('records')
            saved_count = 0

            for record in records:
                from revenue_column_mapping import map_revenue_objective_record
                mapped = map_revenue_objective_record(record, file_upload_id)

                if not mapped.get('dot_name'):
                    continue

                # Get or create DOT
                dot = DOTService.get_or_create_dot(
                    self.db, mapped['dot_name'])
                mapped['dot_id'] = dot.id

                # Check if exists
                existing = self.db.query(RevenueObjective).filter(
                    RevenueObjective.dot_name == mapped['dot_name']
                ).first()

                if existing:
                    # Update
                    for key, value in mapped.items():
                        if key != 'created_at' and hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create
                    objective = RevenueObjective(**mapped)
                    self.db.add(objective)

                saved_count += 1

            self.db.commit()

            return {
                "success": True,
                "processed_rows": len(df_processed),
                "saved_count": saved_count
            }

        except Exception as e:
            logger.error(f"Error processing revenue objectives: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def _read_file(self, file_path: str) -> pd.DataFrame:
        """Read CSV or Excel file"""
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path, low_memory=False)
        elif file_path.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

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
            df[org_name_col] = df[org_name_col].astype(
                str).str.replace('DOT_', '', case=False)
        return df

    def _clean_org_name_separators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Replace – and _ with spaces in Org Name"""
        org_name_col = self._find_column(df, ['Org Name', 'organisation'])
        if org_name_col:
            df[org_name_col] = df[org_name_col].astype(str).str.replace(
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
        # Remove duplicates
        cpt_col = self._find_column(
            df, ['Cpt Comptable', 'account code'])
        if cpt_col:
            df = df.drop_duplicates(subset=[cpt_col])
        return df

    def _process_objectives_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process objectives data"""
        # Clean DOT names
        dot_col = self._find_column(df, ['DOT', 'dot name'])
        if dot_col:
            from services.revenue_processing_helpers import RevenueProcessingHelpers
            df[dot_col] = df[dot_col].apply(
                lambda x: RevenueProcessingHelpers.clean_org_name_for_matching(str(x))
            )
            # Remove duplicates
            df = df.drop_duplicates(subset=[dot_col])
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

            self.db.commit()
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

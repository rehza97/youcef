"""
File Detector Service
Automatically detects KPI file types based on column headers
Maps uploaded files to appropriate processing logic
"""
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum

logger = logging.getLogger(__name__)


class KPIFileType(Enum):
    """Enumeration of supported KPI file types"""
    PARC_CORPORATE_NGBSS = "parc_corporate_ngbss"
    CHIFFRE_AFFAIRES = "chiffre_affaires"  # Main revenue journal file
    CHIFFRE_AFFAIRES_ACCOUNT_DESC = "chiffre_affaires_account_desc"  # File 2: Description Cpt Comptable
    CHIFFRE_AFFAIRES_OBJECTIVE = "chiffre_affaires_objective"  # File 1: Objectif C.A
    ENCAISSEMENT = "encaissement"
    ENCAISSEMENT_AR_DOT = "encaissement_ar_dot"  # NEW: Specialized Encaissement AR DOT module
    CREANCE_PERIODIQUE = "creance_periodique"
    CREANCE_PERIODIQUE_DOT = "creance_periodique_dot"  # NEW: Specialized Créance Périodique DOT module
    DOT_CORPORATE = "dot_corporate"  # NEW: DOT Corporate monthly revenue data
    ANOMALIE = "anomalie"
    UNKNOWN = "unknown"


class FileDetectorService:
    """Service for detecting KPI file types based on headers"""

    def __init__(self):
        # Define signature columns for each KPI file type
        # These are the key columns that uniquely identify each file type
        self.kpi_signatures = {
            KPIFileType.PARC_CORPORATE_NGBSS: {
                'required': [
                    'actel_code', 'actel code',
                    'subscriber_status', 'subscriber status',
                    'telecom_type', 'telecom type',
                    'offer_name', 'offer name',
                    'code_customer_l2', 'code customer l2',
                    'code_customer_l3', 'code customer l3'
                ],
                'min_matches': 4,  # At least 4 of these columns must be present
                'keywords': ['subscriber', 'actel', 'telecom', 'offer']
            },
            KPIFileType.CHIFFRE_AFFAIRES: {
                'required': [
                    'org_name', 'org name', 'organisation', 'org',
                    'date_gl', 'date gl', 'date',
                    'cpt_comptable', 'cpt comptable', 'compte comptable',
                    'prix_uni', 'prix uni', 'prix unitaire',
                    'mnt_ht', 'mnt ht', 'montant ht', 'montant_ht',
                    'mnt_tax', 'mnt tax', 'montant taxe', 'montant_taxe',
                    'mnt_ttc', 'mnt ttc', 'montant ttc', 'montant_ttc',
                    'chiffre_aff_exe_dzd', 'chiffre aff exe dzd', 'chiffre d\'affaires',
                    'type_fact', 'type fact', 'n_fact', 'n fact',
                    'description', 'desc'
                ],
                'min_matches': 5,  # Increased to avoid confusion with support files
                'keywords': ['chiffre', 'affaires', 'journal', 'revenue', 'facture']
            },
            KPIFileType.CHIFFRE_AFFAIRES_ACCOUNT_DESC: {
                'required': [
                    'cpt_comptable', 'cpt comptable', 'compte comptable',
                    'description_cpt_comptable', 'description cpt comptable', 'description',
                    'aut_bdg', 'aut bdg',
                    'aut_imp', 'aut imp',
                    'type_cpte', 'type cpte',
                    'auxil', 'let'
                ],
                'min_matches': 3,  # Must have cpt_comptable, description, and at least one more
                'keywords': ['description', 'comptable', 'account', 'cpt', 'aut']
            },
            KPIFileType.CHIFFRE_AFFAIRES_OBJECTIVE: {
                'required': [
                    'dot',
                    'objectif', 'objectif_ca', 'objectif ca', 'objective', 'objectif c a', 'objectifca'
                ],
                'min_matches': 2,  # Must have both dot and objectif
                'keywords': ['objectif', 'objective', 'ca']
            },
            KPIFileType.ENCAISSEMENT: {
                'required': [
                    'organisation', 'org_name', 'org name',
                    'n_fact', 'n fact',
                    'typ_fact', 'typ fact', 'type_fact',
                    'montant_ht', 'montant ht',
                    'montant_taxe', 'montant taxe',
                    'montant_ttc', 'montant ttc',
                    'encaissement',
                    'date_fact', 'date fact'
                ],
                'min_matches': 5,
                'keywords': ['encaissement', 'facture', 'montant', 'fact']
            },
            KPIFileType.ENCAISSEMENT_AR_DOT: {
                'required': [
                    'organisation', 'org_name', 'org name',
                    'source',
                    'n_fact', 'n fact',
                    'typ_fact', 'typ fact', 'type_fact',
                    'date_fact', 'date fact',
                    'client',
                    'n_client', 'n client',
                    'montant_ht', 'montant ht',
                    'montant_taxe', 'montant taxe',
                    'montant_ttc', 'montant ttc',
                    'chiffre_aff_exe', 'chiffre aff exe',
                    'encaissement',
                    'n_rglt', 'n rglt',
                    'date_rglt', 'date rglt'
                ],
                'min_matches': 8,  # More specific matching to avoid confusion with generic encaissement
                'keywords': ['factures ar', 'etat des factures', 'algerie telecom', 'encaissement', 'rglt']
            },
            KPIFileType.CREANCE_PERIODIQUE: {
                'required': [
                    'dot',
                    'actel',
                    'annee', 'année',
                    'mois',
                    'produit',
                    'cust_lev1', 'cust lev1',
                    'cust_lev2', 'cust lev2',
                    'cust_lev3', 'cust lev3',
                    'invoice_amt', 'invoice amt',
                    'open_amt', 'open amt',
                    'creance_brut', 'creance brut',
                    'creance_net', 'creance net'
                ],
                'min_matches': 10,  # Increased to prioritize DOT version
                'keywords': ['creance', 'créance', 'cust_lev', 'invoice', 'actel']
            },
            KPIFileType.CREANCE_PERIODIQUE_DOT: {
                'required': [
                    'dot',
                    'actel',
                    'annee', 'année',
                    'mois',
                    'produit',
                    'cust_lev1', 'cust lev1',
                    'cust_lev2', 'cust lev2',
                    'cust_lev3', 'cust lev3',
                    'invoice_amt', 'invoice amt',
                    'creance_net', 'creance net'
                ],
                'min_matches': 7,
                'keywords': ['creance', 'créance', 'periodique', 'cust_lev', 'dot']
            },
            KPIFileType.DOT_CORPORATE: {
                'required': [
                    'dot', 'd.o.t', 'direction',
                    'jan', 'janvier', 'janv',
                    'fév', 'février', 'fev', 'feb',
                    'mars', 'mar',
                    'avril', 'avr',
                    'mai', 'may',
                    'juin', 'jun',
                    'juillet', 'jul',
                    'aout', 'août', 'aug',
                    'sept', 'septembre', 'sep',
                    'oct', 'octobre',
                    'nov', 'novembre',
                    'déc', 'décembre', 'dec', 'decembre'
                ],
                'min_matches': 8,  # DOT + at least 7 month columns (high confidence)
                'keywords': ['dot', 'jan', 'fév', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'sept', 'oct', 'nov', 'déc', 'month', 'mois']
            },
            KPIFileType.ANOMALIE: {
                'required': [
                    'anomaly_type', 'anomaly type', 'type_anomalie',
                    'anomaly_description', 'anomaly description',
                    'anomaly_source', 'source'
                ],
                'min_matches': 2,
                'keywords': ['anomaly', 'anomalie']
            }
        }

    def detect_file_type(self, file_path: str) -> Tuple[KPIFileType, Dict[str, any]]:
        """
        Detect the KPI file type by examining its headers

        Args:
            file_path: Path to the file to analyze

        Returns:
            Tuple of (KPIFileType, detection_info)
            detection_info contains:
                - detected_type: The detected KPI type
                - confidence: Confidence score (0-100)
                - matched_columns: List of columns that matched
                - all_columns: All columns in the file
                - reason: Explanation of detection
        """
        try:
            logger.info(f"🔍 Starting file type detection for: {file_path}")

            # Read file headers
            file_path_obj = Path(file_path)
            columns = self._read_file_headers(file_path_obj)

            if not columns:
                logger.warning(f"⚠️ No columns found in file: {file_path}")
                return KPIFileType.UNKNOWN, {
                    'detected_type': KPIFileType.UNKNOWN.value,
                    'confidence': 0,
                    'matched_columns': [],
                    'all_columns': [],
                    'reason': 'No columns found in file'
                }

            logger.info(f"📋 Found {len(columns)} columns")
            logger.info(f"📋 First 10 columns: {columns[:10]}")
            logger.info(f"📋 ALL COLUMNS: {columns}")

            # Normalize columns for comparison
            normalized_columns = self._normalize_columns(columns)

            # Score each KPI type
            scores = {}
            details = {}

            for kpi_type, signature in self.kpi_signatures.items():
                score, matched = self._calculate_match_score(
                    normalized_columns,
                    signature
                )
                scores[kpi_type] = score
                details[kpi_type] = matched

                logger.debug(
                    f"  {kpi_type.value}: score={score}, matched={len(matched)} columns")

            # Find best match
            best_match = max(scores, key=scores.get)
            best_score = scores[best_match]
            matched_columns = details[best_match]

            # Determine confidence
            confidence = min(best_score * 10, 100)  # Convert to 0-100 scale

            # Log detection scores for all types
            logger.info("🎯 Detection Scores:")
            for kpi_type, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]:
                logger.info(f"   {kpi_type.value}: {score:.1f} points ({min(score*10, 100):.0f}% confidence)")

            # Require minimum confidence to classify
            if confidence < 40 or best_match == KPIFileType.UNKNOWN:
                detected_type = KPIFileType.UNKNOWN
                reason = f"Low confidence ({confidence}%). Unable to definitively classify file."
            else:
                detected_type = best_match
                reason = f"Matched {len(matched_columns)} signature columns with {confidence}% confidence"

            detection_info = {
                'detected_type': detected_type.value,
                'confidence': round(confidence, 2),
                'matched_columns': matched_columns,
                'all_columns': columns,
                'reason': reason,
                'scores': {k.value: v for k, v in scores.items()}
            }

            logger.info(
                f"✅ Detection complete: {detected_type.value} ({confidence}% confidence)")
            logger.info(f"   Matched {len(matched_columns)} signature columns: {matched_columns[:10]}")
            if len(matched_columns) > 10:
                logger.info(f"   ... and {len(matched_columns) - 10} more")

            return detected_type, detection_info

        except Exception as e:
            logger.error(f"❌ Error detecting file type: {str(e)}")
            return KPIFileType.UNKNOWN, {
                'detected_type': KPIFileType.UNKNOWN.value,
                'confidence': 0,
                'matched_columns': [],
                'all_columns': [],
                'reason': f'Error during detection: {str(e)}'
            }

    def _read_file_headers(self, file_path: Path) -> List[str]:
        """Read column headers from a file, searching first 20 rows for header row"""
        try:
            file_ext = file_path.suffix.lower()

            if file_ext == '.csv':
                # Try different encodings and delimiters for CSV
                # Search for headers in first 20 rows
                for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                    for delimiter in [',', ';', '\t', '|']:
                        try:
                            # Read first 20 rows to find headers
                            df_sample = pd.read_csv(
                                file_path, nrows=20, encoding=encoding, sep=delimiter, header=None)

                            # Search for header row in first 20 rows
                            header_row = self._find_header_row(df_sample)

                            if header_row is not None:
                                # Re-read with correct header row
                                df = pd.read_csv(
                                    file_path, nrows=0, encoding=encoding, sep=delimiter, header=header_row)
                                # Check if we got multiple columns (good delimiter)
                                if len(df.columns) > 1:
                                    logger.info(
                                        f"✅ Found CSV headers at row {header_row} with encoding={encoding}, delimiter={delimiter}")
                                    return df.columns.tolist()
                        except (UnicodeDecodeError, pd.errors.ParserError):
                            continue

                # If all fail, try with error handling and default delimiter
                df = pd.read_csv(file_path, nrows=0,
                                 encoding='utf-8', on_bad_lines='skip')
                return df.columns.tolist()

            elif file_ext == '.xlsx':
                # Read modern Excel file - search first 20 rows for headers
                df_sample = pd.read_excel(file_path, nrows=20, sheet_name=0, engine='openpyxl', header=None)
                header_row = self._find_header_row(df_sample)

                if header_row is not None:
                    df = pd.read_excel(file_path, nrows=0, sheet_name=0, engine='openpyxl', header=header_row)
                    logger.info(f"✅ Found Excel headers at row {header_row}")
                    return df.columns.tolist()
                else:
                    # Fallback to first row
                    df = pd.read_excel(file_path, nrows=0, sheet_name=0, engine='openpyxl')
                    return df.columns.tolist()

            elif file_ext == '.xls':
                # Read old Excel file (first sheet) - needs xlrd engine
                try:
                    # Try reading first 20 rows to find headers
                    df_sample = pd.read_excel(file_path, nrows=20, sheet_name=0, engine='xlrd', header=None)
                    header_row = self._find_header_row(df_sample)

                    if header_row is not None:
                        df = pd.read_excel(file_path, nrows=0, sheet_name=0, engine='xlrd', header=header_row)
                        logger.info(f"✅ Found .xls headers at row {header_row}")
                        return df.columns.tolist()
                    else:
                        df = pd.read_excel(file_path, nrows=0, sheet_name=0, engine='xlrd')
                        return df.columns.tolist()
                except Exception as e:
                    logger.warning(
                        f"⚠️ Failed to read .xls with xlrd: {str(e)}")
                    # Some systems export HTML with .xls extension; try parsing HTML tables
                    try:
                        # First read without header to detect structure
                        html_tables_raw = pd.read_html(file_path, header=None)
                        if html_tables_raw:
                            logger.info(
                                "✅ Parsed HTML table from .xls masquerading as HTML")
                            # Search through tables for best header match
                            for idx, table in enumerate(html_tables_raw):
                                if len(table.columns) > 10:  # Likely the data table
                                    logger.info(f"   Using table {idx} with {len(table.columns)} columns")
                                    # Search first 20 rows for header row
                                    header_row = self._find_header_row(table.head(20).reset_index(drop=True))

                                    if header_row is not None:
                                        # Extract headers from the detected row
                                        headers = table.iloc[header_row].astype(str).tolist()
                                        logger.info(f"✅ Found HTML table headers at row {header_row}")
                                        logger.info(f"   Headers: {headers[:5]}... (showing first 5)")
                                        return headers
                                    else:
                                        # If no header row found, assume first row is header
                                        logger.info(f"   No clear header row found, using row 0")
                                        headers = table.iloc[0].astype(str).tolist()
                                        return headers
                            # Fallback to first table, first row as headers
                            return html_tables_raw[0].iloc[0].astype(str).tolist()
                    except Exception as e2:
                        logger.warning(f"⚠️ pandas.read_html failed: {e2}")
                    # As a last resort, try openpyxl (unlikely to work for .xls)
                    try:
                        df = pd.read_excel(
                            file_path, nrows=0, sheet_name=0, engine='openpyxl')
                        return df.columns.tolist()
                    except Exception as e3:
                        logger.error(
                            f"❌ Failed to read .xls with any engine: {e3}")
                        return []
            else:
                logger.warning(f"⚠️ Unsupported file type: {file_ext}")
                return []

        except Exception as e:
            logger.error(f"❌ Error reading file headers: {str(e)}")
            return []

    def _find_header_row(self, df_sample: pd.DataFrame) -> Optional[int]:
        """
        Search first 20 rows to find the header row containing known file type headers

        Args:
            df_sample: DataFrame with first 20 rows (header=None)

        Returns:
            Row index (0-based) where headers are found, or None if not found
        """
        # Define key headers for different file types
        # These should be distinctive enough to avoid false positives
        header_sets = {
            'revenue_journal': [
                'org name', 'date fact', 'cpt comptable',
                'date gl', 'mnt ht', 'mnt ttc', 'chiffre aff exe dzd',
                'typ fact', 'delai paie'
            ],
            'parc_corporate': [
                'actel code', 'actel', 'customer level',
                'telecom type', 'primary offer', 'subscriber status',
                'offer type', 'price plan', 'activation date'
            ],
            'creance_periodique': [
                'dot', 'actel', 'mois', 'annee', 'année',
                'produit', 'cust lev1', 'cust lev2', 'cust lev3',
                'invoice amt', 'open amt', 'creance brut', 'creance net',
                'subs status', 'dispute amt'
            ],
            'encaissement': [
                'organisation', 'source', 'n fact', 'typ fact',
                'montant ht', 'montant ttc', 'encaissement',
                'chiffre aff exe', 'date rglt', 'taux encaissement'
            ]
        }

        best_row = None
        best_match_count = 0
        best_file_type = None

        # Search through first 20 rows
        for row_idx in range(min(20, len(df_sample))):
            row_values = df_sample.iloc[row_idx].astype(str).str.lower().str.strip()

            # Log first few rows for debugging
            if row_idx < 5:
                logger.debug(f"Row {row_idx}: {list(row_values[:5])}")

            # Try each header set
            for file_type, key_headers in header_sets.items():
                # Count how many key headers are present in this row
                match_count = 0
                matched_headers = []

                for header in key_headers:
                    for cell_value in row_values:
                        # Normalize cell value
                        cell_normalized = ''.join(c if c.isalnum() or c == ' ' else ' ' for c in cell_value)
                        cell_normalized = ' '.join(cell_normalized.split())

                        # More strict matching to avoid false positives:
                        # 1. For multi-word headers, require most words to match
                        # 2. Avoid matching very short words unless they're exact
                        header_words = header.split()

                        if len(header_words) == 1:
                            # Single word: require exact match or cell starts/ends with it
                            # and cell is not too long (to avoid matching "actel" in "Actel Code_Code d'actel")
                            if (cell_normalized == header or
                                (header in cell_normalized and len(cell_normalized) <= len(header) + 10)):
                                match_count += 1
                                matched_headers.append(header)
                                break
                        else:
                            # Multi-word: require at least half the words to match
                            words_matched = sum(1 for word in header_words if word in cell_normalized)
                            if words_matched >= len(header_words) / 2:
                                match_count += 1
                                matched_headers.append(header)
                                break

                # If this row has more matches, it's likely the header row
                if match_count > best_match_count:
                    best_match_count = match_count
                    best_row = row_idx
                    best_file_type = file_type
                    logger.debug(f"  Row {row_idx} - {file_type}: {match_count} matches ({matched_headers[:3]})")

        # Require at least 4 matching headers to consider it valid
        if best_match_count >= 4:
            logger.info(f"🎯 Found {best_file_type} header row at index {best_row} with {best_match_count} matching headers")
            return best_row
        else:
            logger.warning(f"⚠️ No clear header row found in first 20 rows (best match: {best_match_count} headers)")
            return None

    def _normalize_columns(self, columns: List[str]) -> Set[str]:
        """
        Normalize column names for comparison
        - Convert to lowercase
        - Remove special characters
        - Remove extra spaces
        - Create variations
        - Handle multi-language columns (e.g., "Column_Colonne")
        """
        normalized = set()

        for col in columns:
            # Basic normalization
            col_norm = str(col).lower().strip()

            # Split on underscore to handle bilingual columns like "Actel Code_Code d'actel"
            parts = col_norm.split('_')

            for part in parts:
                # Remove special characters but keep spaces
                part_clean = ''.join(c if c.isalnum() or c in [
                                     ' '] else ' ' for c in part)

                # Remove extra spaces
                part_clean = ' '.join(part_clean.split())

                if part_clean:
                    # Add variations
                    normalized.add(part_clean)  # With spaces
                    normalized.add(part_clean.replace(
                        ' ', '_'))  # With underscores
                    normalized.add(part_clean.replace(
                        ' ', ''))  # No separators

            # Also process the full column name
            col_clean = ''.join(c if c.isalnum() or c in [
                                ' ', '_'] else ' ' for c in col_norm)
            col_clean = ' '.join(col_clean.split())

            if col_clean:
                normalized.add(col_clean)
                normalized.add(col_clean.replace(' ', '_'))
                normalized.add(col_clean.replace(' ', ''))
                normalized.add(col_clean.replace('_', ' '))

            # Add original (case-insensitive)
            normalized.add(col_norm)

        return normalized

    def _calculate_match_score(
        self,
        normalized_columns: Set[str],
        signature: Dict
    ) -> Tuple[int, List[str]]:
        """
        Calculate match score for a signature

        Returns:
            Tuple of (score, matched_columns)
        """
        required_cols = signature['required']
        min_matches = signature['min_matches']
        keywords = signature.get('keywords', [])

        matched_columns = []

        # Check for required column matches
        for req_col in required_cols:
            req_col_norm = req_col.lower().strip()
            if req_col_norm in normalized_columns:
                matched_columns.append(req_col)

        # Base score from column matches
        column_score = len(matched_columns)

        # Bonus points for keyword matches
        keyword_bonus = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Check if keyword appears in any column name
            for col in normalized_columns:
                if keyword_lower in col:
                    keyword_bonus += 0.5
                    break

        # Total score
        total_score = column_score + keyword_bonus

        # Apply penalty if minimum matches not met
        if column_score < min_matches:
            total_score = total_score * 0.5

        return total_score, matched_columns

    def get_processor_for_type(self, kpi_type: KPIFileType) -> Optional[str]:
        """
        Get the appropriate processor class name for a KPI type

        Returns:
            String name of the processor class, or None if unknown
        """
        processor_mapping = {
            KPIFileType.PARC_CORPORATE_NGBSS: 'ParcCorporateNGBSSETL',
            KPIFileType.CHIFFRE_AFFAIRES: 'ChiffreAffairesETL',
            KPIFileType.CHIFFRE_AFFAIRES_ACCOUNT_DESC: 'ChiffreAffairesAccountDescETL',
            KPIFileType.CHIFFRE_AFFAIRES_OBJECTIVE: 'ChiffreAffairesObjectiveETL',
            KPIFileType.ENCAISSEMENT: 'EncaissementETL',
            KPIFileType.ENCAISSEMENT_AR_DOT: 'EncaissementARDotETL',  # NEW: Specialized module
            KPIFileType.CREANCE_PERIODIQUE: 'CreancePeriodique ETL',
            KPIFileType.CREANCE_PERIODIQUE_DOT: 'CreancePeriodiqueDotETL',  # NEW: Specialized module
            KPIFileType.DOT_CORPORATE: 'DotCorporateETL',  # NEW: DOT Corporate monthly revenue
            KPIFileType.ANOMALIE: None,  # Anomalies are output, not processed
            KPIFileType.UNKNOWN: None
        }

        return processor_mapping.get(kpi_type)

    def get_processing_requirements(self, kpi_type: KPIFileType) -> Dict[str, any]:
        """
        Get processing requirements and metadata for a KPI type

        Returns:
            Dictionary with processing requirements
        """
        requirements = {
            KPIFileType.PARC_CORPORATE_NGBSS: {
                'name': 'Parc Corporate NGBSS',
                'description': 'Corporate subscriber park data',
                'required_columns': ['actel_code', 'subscriber_status', 'telecom_type', 'offer_name'],
                'processor': 'ParcCorporateNGBSSETL',
                'generates_anomalies': True,
                'estimated_processing_time': 'medium'
            },
            KPIFileType.CHIFFRE_AFFAIRES: {
                'name': 'Chiffre d\'Affaires AR DOT - Journal (File 3/3)',
                'description': 'Main revenue journal file (requires 3 files total)',
                'required_columns': ['org_name', 'date_gl', 'cpt_comptable', 'chiffre_aff_exe_dzd'],
                'processor': 'ChiffreAffairesETL',
                'generates_anomalies': True,
                'estimated_processing_time': 'medium',
                'notes': 'Main file of 3-file set. Process with: 1) Objectif C.A, 2) Description Cpt Comptable, 3) Journal (this file)'
            },
            KPIFileType.CHIFFRE_AFFAIRES_ACCOUNT_DESC: {
                'name': 'Chiffre d\'Affaires AR DOT - Description Cpt Comptable (File 2/3)',
                'description': 'Account code descriptions for revenue module',
                'required_columns': ['cpt_comptable', 'description_cpt_comptable', 'aut_bdg', 'type_cpte'],
                'processor': 'ChiffreAffairesAccountDescETL',
                'generates_anomalies': False,
                'estimated_processing_time': 'fast',
                'notes': 'Part of Chiffre d\'Affaires 3-file set. Upload File 1 (Objectif) first, then this file, then File 3 (Journal)'
            },
            KPIFileType.CHIFFRE_AFFAIRES_OBJECTIVE: {
                'name': 'Chiffre d\'Affaires AR DOT - Objectif C.A (File 1/3)',
                'description': 'Revenue objectives by DOT for revenue module',
                'required_columns': ['dot', 'objectif_ca'],
                'processor': 'ChiffreAffairesObjectiveETL',
                'generates_anomalies': False,
                'estimated_processing_time': 'fast',
                'notes': 'Part of Chiffre d\'Affaires 3-file set. Upload this file FIRST, then File 2 (Description), then File 3 (Journal)'
            },
            KPIFileType.ENCAISSEMENT: {
                'name': 'Encaissement AR DOT',
                'description': 'Collection and payment data',
                'required_columns': ['organisation', 'n_fact', 'montant_ttc', 'encaissement'],
                'processor': 'EncaissementETL',
                'generates_anomalies': True,
                'estimated_processing_time': 'medium',
                'notes': 'Can process multiple years (current and N-1)'
            },
            KPIFileType.ENCAISSEMENT_AR_DOT: {
                'name': 'Encaissement AR DOT (Factures AR)',
                'description': 'Specialized Encaissement AR with duplicate detection and Taux calculation',
                'required_columns': ['organisation', 'source', 'n_fact', 'typ_fact', 'montant_ttc', 'encaissement', 'chiffre_aff_exe'],
                'processor': 'EncaissementARDotETL',
                'generates_anomalies': True,
                'estimated_processing_time': 'medium',
                'notes': 'Processes Algérie Télécom AR invoices. Includes: AT_SIEGE removal, duplicate detection via composite key, Taux d\'encaissement calculation, multi-year support.'
            },
            KPIFileType.CREANCE_PERIODIQUE: {
                'name': 'Créance Périodique DOT',
                'description': 'Periodic debt and credit data',
                'required_columns': ['dot', 'actel', 'annee', 'mois', 'produit'],
                'processor': 'CreancePeriodiqueETL',
                'generates_anomalies': True,
                'estimated_processing_time': 'medium'
            },
            KPIFileType.CREANCE_PERIODIQUE_DOT: {
                'name': 'Créance Périodique DOT (Specialized)',
                'description': 'Specialized periodic debt tracking with customer level filtering',
                'required_columns': ['dot', 'actel', 'annee', 'mois', 'produit', 'cust_lev1', 'cust_lev2', 'cust_lev3', 'creance_net'],
                'processor': 'CreancePeriodiqueDotETL',
                'generates_anomalies': False,
                'estimated_processing_time': 'medium',
                'notes': 'Applies 10 business rules for filtering and cleaning. Filters: Residential/Startup PME TPE/VIP-AT (CUST_LEV1), Scolaires/Convention/KMS/PME (CUST_LEV2), ADSL/FTTX/PSTN/VOIP/X25/XDSL (PRODUIT). Generates 5 aggregate views for dashboard.'
            },
            KPIFileType.DOT_CORPORATE: {
                'name': 'Chiffre d\'Affaire DOT Corporate',
                'description': 'Monthly revenue data by DOT',
                'required_columns': ['dot', 'jan', 'fév', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'sept', 'oct', 'nov', 'déc'],
                'processor': 'DotCorporateETL',
                'generates_anomalies': False,
                'estimated_processing_time': 'fast',
                'notes': 'Monthly revenue figures by DOT. Automatically sets current year for filtering.'
            },
            KPIFileType.ANOMALIE: {
                'name': 'Anomalie',
                'description': 'Anomaly records from other KPI processing',
                'required_columns': ['anomaly_type', 'anomaly_description'],
                'processor': None,
                'generates_anomalies': False,
                'estimated_processing_time': 'none',
                'notes': 'Generated automatically, not processed'
            },
            KPIFileType.UNKNOWN: {
                'name': 'Unknown',
                'description': 'File type could not be determined',
                'required_columns': [],
                'processor': None,
                'generates_anomalies': False,
                'estimated_processing_time': 'none'
            }
        }

        return requirements.get(kpi_type, requirements[KPIFileType.UNKNOWN])


# Singleton instance
file_detector_service = FileDetectorService()

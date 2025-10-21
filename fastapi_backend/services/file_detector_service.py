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
    CHIFFRE_AFFAIRES = "chiffre_affaires"
    ENCAISSEMENT = "encaissement"
    CREANCE_PERIODIQUE = "creance_periodique"
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
                'min_matches': 4,
                'keywords': ['chiffre', 'affaires', 'ca', 'comptable', 'objectif', 'journal', 'revenue']
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
                'min_matches': 6,
                'keywords': ['creance', 'créance', 'cust_lev', 'invoice', 'actel']
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

            logger.info(f"📋 Found {len(columns)} columns: {columns[:10]}...")
            logger.info(f"📋 All columns: {columns}")

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
            logger.info(f"   Matched columns: {matched_columns}")

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
        """Read column headers from a file"""
        try:
            file_ext = file_path.suffix.lower()

            if file_ext == '.csv':
                # Try different encodings and delimiters for CSV
                for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                    for delimiter in [',', ';', '\t', '|']:
                        try:
                            df = pd.read_csv(
                                file_path, nrows=0, encoding=encoding, sep=delimiter)
                            # Check if we got multiple columns (good delimiter)
                            if len(df.columns) > 1:
                                logger.debug(
                                    f"Successfully read CSV with encoding={encoding}, delimiter={delimiter}")
                                return df.columns.tolist()
                        except (UnicodeDecodeError, pd.errors.ParserError):
                            continue

                # If all fail, try with error handling and default delimiter
                df = pd.read_csv(file_path, nrows=0,
                                 encoding='utf-8', errors='ignore')
                return df.columns.tolist()

            elif file_ext == '.xlsx':
                # Read modern Excel file (first sheet)
                df = pd.read_excel(file_path, nrows=0,
                                   sheet_name=0, engine='openpyxl')
                return df.columns.tolist()

            elif file_ext == '.xls':
                # Read old Excel file (first sheet) - needs xlrd engine
                try:
                    df = pd.read_excel(file_path, nrows=0,
                                       sheet_name=0, engine='xlrd')
                    return df.columns.tolist()
                except Exception as e:
                    logger.warning(
                        f"⚠️ Failed to read .xls with xlrd: {str(e)}")
                    # Some systems export HTML with .xls extension; try parsing HTML tables
                    try:
                        html_tables = pd.read_html(file_path, header=0)
                        if html_tables:
                            logger.info(
                                "✅ Parsed HTML table from .xls masquerading as HTML")
                            return html_tables[0].columns.astype(str).tolist()
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
            KPIFileType.ENCAISSEMENT: 'EncaissementETL',
            KPIFileType.CREANCE_PERIODIQUE: 'CreancePeriodique ETL',
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
                'name': 'Chiffre d\'Affaires AR DOT',
                'description': 'Revenue data with objectives',
                'required_columns': ['org_name', 'date_gl', 'cpt_comptable', 'chiffre_aff_exe_dzd'],
                'processor': 'ChiffreAffairesETL',
                'generates_anomalies': True,
                'estimated_processing_time': 'medium'
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
            KPIFileType.CREANCE_PERIODIQUE: {
                'name': 'Créance Périodique DOT',
                'description': 'Periodic debt and credit data',
                'required_columns': ['dot', 'actel', 'annee', 'mois', 'produit'],
                'processor': 'CreancePeriodiqueETL',
                'generates_anomalies': True,
                'estimated_processing_time': 'medium'
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

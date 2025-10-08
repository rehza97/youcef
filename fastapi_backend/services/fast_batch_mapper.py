"""
Fast Batch Column Mapping for Park Data
Maps DataFrames directly without row-by-row iteration
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class FastBatchMapper:
    """Fast vectorized column mapper for park data"""

    def __init__(self):
        self._column_cache = {}  # Cache normalized column mappings

    def _normalize_column_name(self, col: str) -> str:
        """Normalize column name for matching"""
        if col is None:
            return ""
        return (
            str(col).lower()
            .replace("_", " ")
            .replace("-", " ")
            .replace("'", "'")
            .replace("'", "'")
            .strip()
        )

    def _find_column(self, df: pd.DataFrame, keywords: list) -> str:
        """Find column by keywords (cached)"""
        cache_key = "|".join(keywords)

        if cache_key in self._column_cache:
            return self._column_cache[cache_key]

        # Normalize all column names once
        norm_map = {self._normalize_column_name(
            col): col for col in df.columns}
        norm_keywords = [self._normalize_column_name(k) for k in keywords]

        # Try exact match with all keywords
        for norm_col, orig_col in norm_map.items():
            if all(kw in norm_col for kw in norm_keywords):
                self._column_cache[cache_key] = orig_col
                return orig_col

        # Try partial match with any keyword
        for norm_col, orig_col in norm_map.items():
            if any(kw in norm_col for kw in norm_keywords):
                self._column_cache[cache_key] = orig_col
                return orig_col

        self._column_cache[cache_key] = None
        return None

    def map_dataframe_to_parks(self, df: pd.DataFrame, file_upload_id: int) -> pd.DataFrame:
        """
        ✅ FAST: Map entire DataFrame at once using vectorized operations
        Instead of 4698 function calls, we do ~50 column operations
        """
        try:
            result = pd.DataFrame()

            # Helper to safely get column
            def get_col(keywords, default=None):
                col = self._find_column(df, keywords)
                if col and col in df.columns:
                    return df[col]
                return pd.Series([default] * len(df), index=df.index)

            # Map all columns using vectorized operations
            result['file_upload_id'] = file_upload_id
            result['extraction_date'] = pd.to_datetime(
                get_col(["extraction date", "extraction"]),
                errors='coerce',
                dayfirst=True
            )
            result['dot_name'] = get_col(["dot"]).astype(str).str.strip()
            result['actel_code'] = get_col(
                ["actel code", "actel"]).astype(str).str.strip()
            result['telecom_type'] = get_col(
                ["telecom type", "service", "produit"]).astype(str).str.strip()
            result['offer_type'] = get_col(
                ["offer type", "offre"]).astype(str).str.strip()
            result['offer_name'] = get_col(
                ["offer name", "offre"]).astype(str).str.strip()
            result['rental_fees'] = pd.to_numeric(
                get_col(["rental fees", "abonnement"]).astype(
                    str).str.replace(",", "."),
                errors='coerce'
            )
            result['customer_l1_code'] = get_col(
                ["code customer l1", "customer l1"]).astype(str).str.strip()
            result['customer_l1_description'] = get_col(
                ["description customer l1", "customer l1 description"]).astype(str).str.strip()
            result['customer_l2_code'] = get_col(
                ["code customer l2", "customer l2"]).astype(str).str.strip()
            result['customer_l2_description'] = get_col(
                ["description customer l2", "customer l2 description"]).astype(str).str.strip()
            result['customer_l3_code'] = get_col(
                ["code customer l3", "customer l3"]).astype(str).str.strip()
            result['customer_l3_description'] = get_col(
                ["description customer l3", "customer l3 description"]).astype(str).str.strip()
            result['customer_code'] = get_col(
                ["customer code", "ncli"]).astype(str).str.strip()
            result['service_number'] = get_col(
                ["service number", "nd"]).astype(str).str.strip()
            result['related_service_number'] = get_col(
                ["related service number"]).astype(str).str.strip()
            result['username'] = get_col(["username"]).astype(str).str.strip()
            result['subscriber_status'] = get_col(
                ["subscriber status", "abonne"]).astype(str).str.strip()
            result['status_date'] = pd.to_datetime(
                get_col(["status date", "statut"]), errors='coerce', dayfirst=True)
            result['creation_date'] = pd.to_datetime(
                get_col(["creation date", "creation"]), errors='coerce', dayfirst=True)
            result['active_date'] = pd.to_datetime(
                get_col(["active date", "activation"]), errors='coerce', dayfirst=True)
            result['csr_name'] = get_col(["csr name"]).astype(str).str.strip()
            result['department_name'] = get_col(
                ["department name"]).astype(str).str.strip()
            result['state'] = get_col(
                ["state", "wilaya"]).astype(str).str.strip()
            result['area'] = get_col(["area", "daira"]).astype(str).str.strip()
            result['town'] = get_col(
                ["town", "commune"]).astype(str).str.strip()
            result['grid'] = get_col(
                ["grid", "quartier"]).astype(str).str.strip()
            result['street'] = get_col(
                ["street", "voie"]).astype(str).str.strip()
            result['street_number'] = get_col(
                ["street number", "numero de voie"]).astype(str).str.strip()
            result['building_no'] = get_col(
                ["building no", "batiment"]).astype(str).str.strip()
            result['unit'] = get_col(
                ["unit", "escalier"]).astype(str).str.strip()
            result['floor'] = get_col(
                ["floor", "etage"]).astype(str).str.strip()
            result['house_no'] = get_col(
                ["house no", "numero de maison"]).astype(str).str.strip()
            result['additional_address_info'] = get_col(
                ["additional address information", "complément d'adresse"]).astype(str).str.strip()
            result['customer_full_name'] = get_col(
                ["customer full name", "nom et prenom"]).astype(str).str.strip()
            result['province'] = get_col(
                ["province", "wilaya"]).astype(str).str.strip()
            result['district'] = get_col(
                ["district", "daira"]).astype(str).str.strip()
            result['city'] = get_col(
                ["city", "commune"]).astype(str).str.strip()
            result['postal_code'] = get_col(
                ["postal code", "code postal"]).astype(str).str.strip()
            # Handle expiry date - convert "UNKNOWN" to None
            expiry_col = get_col(["expiry date", "expiration"])
            expiry_col = expiry_col.replace('UNKNOWN', None)
            result['expiry_date'] = pd.to_datetime(
                expiry_col, errors='coerce', dayfirst=True)
            # Handle ICCID, IMSI, contact_number - convert "UNKNOWN" to None
            iccid_col = get_col(["iccid", "sim"]).astype(str).str.strip()
            iccid_col = iccid_col.replace('UNKNOWN', None)
            result['iccid'] = iccid_col

            imsi_col = get_col(["imsi"]).astype(str).str.strip()
            imsi_col = imsi_col.replace('UNKNOWN', None)
            result['imsi'] = imsi_col

            contact_col = get_col(
                ["contact number", "numéro de contact"]).astype(str).str.strip()
            contact_col = contact_col.replace('UNKNOWN', None)
            result['contact_number'] = contact_col

            # Add timestamps
            result['created_at'] = datetime.utcnow()
            result['updated_at'] = datetime.utcnow()

            # Replace empty strings with None for proper NULL handling
            result = result.replace({'None': None, '': None, 'nan': None})

            logger.debug(f"✅ Fast batch mapped {len(result)} records")
            return result

        except Exception as e:
            logger.error(f"❌ Fast batch mapping failed: {e}")
            raise


# Global instance
fast_mapper = FastBatchMapper()

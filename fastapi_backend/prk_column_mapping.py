#!/usr/bin/env python3
"""
PRK File Column Mapping
Maps actual PRK file headers to database fields
"""

# Exact PRK headers provided
PRK_HEADERS = [
    "Extraction Date_Date d ‘extraction",
    "DOT",
    "Actel Code_Code d’actel",
    "Code Customer L1_Code Catégorie level 1",
    "Description Customer L1_Nom du Catégorie level 1",
    "Code Customer L2_Code Catégorie level 2",
    "Description Customer L2_Nom du Catégorie level 2",
    "Code Customer L3_Code Catégorie level 3",
    "Description Customer L3_Nom du Catégorie level 3",
    "Telecom type_SERVICE / PRODUIT",
    "Offer Type_Type d’offre",
    "Offer name_Nom de l’offre",
    "Rental Fees_Frais d’abonnement",
    "Customer code_NCLI",
    "Service number_ND",
    "Related Service Number_Numero de service correspondant",
    "USERNAME_Nom d’utilisateur",
    "Subscriber status_Status de l’abonne",
    "Status date_Date du statut",
    "Creation Date_Date de creation",
    "Active Date_Date d'activation",
    "CSR Name_Nom CSR",
    "Department Name_Nom de département1",
    "State_Wilaya",
    "Area_Daira",
    "Town_Commune",
    "Grid_Quartier",
    "Street_Voie",
    "Street Number_Numero De Voie",
    "Building No._Batiment",
    "Unit_Escalier",
    "Floor_Etage",
    "House No._Numero de maison",
    "Additional Address Information_Complément d'adresse",
    "Customer full name_NOM ET PRENOM",
    "Province_Wilaya",
    "District_Daira",
    "City_Commune",
    "Postal Code_Code postal",
    "Expiry Date_Date d’expiration",
    "ICCID_N° SIM",
    "IMSI_IMSI",
    "Contact number_Numéro de contact"
]

# Mapping from PRK headers to database fields
PRK_TO_DB_MAPPING = {
    # Core
    "Extraction Date_Date d ‘extraction": "extraction_date",
    "DOT": "dot_name",
    "Actel Code_Code d’actel": "actel_code",

    # Customer hierarchy
    "Code Customer L1_Code Catégorie level 1": "customer_l1_code",
    "Description Customer L1_Nom du Catégorie level 1": "customer_l1_description",
    "Code Customer L2_Code Catégorie level 2": "customer_l2_code",
    "Description Customer L2_Nom du Catégorie level 2": "customer_l2_description",
    "Code Customer L3_Code Catégorie level 3": "customer_l3_code",
    "Description Customer L3_Nom du Catégorie level 3": "customer_l3_description",

    # Offer / product
    "Telecom type_SERVICE / PRODUIT": "telecom_type",
    "Offer Type_Type d’offre": "offer_type",
    "Offer name_Nom de l’offre": "offer_name",
    "Rental Fees_Frais d’abonnement": "rental_fees",

    # Identifiers
    "Customer code_NCLI": "customer_code",
    "Service number_ND": "service_number",
    "Related Service Number_Numero de service correspondant": "related_service_number",
    "USERNAME_Nom d’utilisateur": "username",

    # Status & dates
    "Subscriber status_Status de l’abonne": "subscriber_status",
    "Status date_Date du statut": "status_date",
    "Creation Date_Date de creation": "creation_date",
    "Active Date_Date d'activation": "active_date",

    # Misc / address
    "CSR Name_Nom CSR": "csr_name",
    "Department Name_Nom de département1": "department_name",
    "State_Wilaya": "state",
    "Area_Daira": "area",
    "Town_Commune": "town",
    "Grid_Quartier": "grid",
    "Street_Voie": "street",
    "Street Number_Numero De Voie": "street_number",
    "Building No._Batiment": "building_no",
    "Unit_Escalier": "unit",
    "Floor_Etage": "floor",
    "House No._Numero de maison": "house_no",
    "Additional Address Information_Complément d'adresse": "additional_address_info",
    "Customer full name_NOM ET PRENOM": "customer_full_name",
    "Province_Wilaya": "province",
    "District_Daira": "district",
    "City_Commune": "city",
    "Postal Code_Code postal": "postal_code",
    "Expiry Date_Date d’expiration": "expiry_date",
    "ICCID_N° SIM": "iccid",
    "IMSI_IMSI": "imsi",
    "Contact number_Numéro de contact": "contact_number",
}


def get_prk_column_mapping():
    """Get the mapping from PRK headers to database fields"""
    return PRK_TO_DB_MAPPING


def map_prk_record_to_park_dict(record: dict, file_upload_id: int = None) -> dict:
    """Map a PRK record to Park dictionary with robust header matching."""
    from datetime import datetime
    import pandas as pd

    def _norm(s):
        if s is None:
            return ""
        return (
            str(s).lower()
            .replace("_", " ")
            .replace("-", " ")
            .replace("’", "'")
            .replace("‘", "'")
            .strip()
        )

    keys = list(record.keys())
    norm_map = {_norm(k): k for k in keys}

    def _find(keywords):
        tokens = [_norm(t) for t in keywords]
        for nk, orig in norm_map.items():
            if all(t in nk for t in tokens):
                return orig
        for nk, orig in norm_map.items():
            if any(t in nk for t in tokens):
                return orig
        return None

    def _get(keywords, default=None):
        k = _find(keywords)
        return record.get(k, default) if k else default

    def _s(v):
        if v is None:
            return None
        t = str(v).strip()
        return t if t else None

    def _f(v):
        if v is None:
            return None
        t = str(v).strip()
        if not t:
            return None
        try:
            return float(t.replace(",", "."))
        except Exception:
            return None

    def _d(v):
        if v is None:
            return None
        t = str(v).strip()
        if not t:
            return None
        try:
            # Try standard ISO format first (most common: YYYY-MM-DD HH:MM:SS)
            return pd.to_datetime(t, format="%Y-%m-%d %H:%M:%S", errors="coerce").to_pydatetime()
        except (ValueError, TypeError):
            try:
                # Fallback to general parsing without dayfirst (since our data is year-first)
                return pd.to_datetime(t, errors="coerce", dayfirst=False).to_pydatetime()
            except Exception:
                return None

    park_dict = {
        "file_upload_id": file_upload_id,
        "extraction_date": _d(_get(["extraction date", "extraction"])),
        "dot_name": _s(_get(["dot"])),  # Extract DOT name from file
        "actel_code": _s(_get(["actel code", "actel"])),
        "telecom_type": _s(_get(["telecom type", "service", "produit"])),
        "offer_type": _s(_get(["offer type", "offre"])),
        "offer_name": _s(_get(["offer name", "offre"])),
        "rental_fees": _f(_get(["rental fees", "abonnement"])),
        "customer_code": _s(_get(["customer code", "ncli"])),
        "service_number": _s(_get(["service number", "nd"])),
        "related_service_number": _s(_get(["related service number"])),
        "username": _s(_get(["username"])),
        "subscriber_status": _s(_get(["subscriber status", "abonne"])),
        "status_date": _d(_get(["status date", "statut"])),
        "creation_date": _d(_get(["creation date", "creation"])),
        "active_date": _d(_get(["active date", "activation"])),
        "csr_name": _s(_get(["csr name"])),
        "department_name": _s(_get(["department name"])),
        "state": _s(_get(["state", "wilaya"])),
        "area": _s(_get(["area", "daira"])),
        "town": _s(_get(["town", "commune"])),
        "grid": _s(_get(["grid", "quartier"])),
        "street": _s(_get(["street", "voie"])),
        "street_number": _s(_get(["street number", "numero de voie"])),
        "building_no": _s(_get(["building no", "batiment"])),
        "unit": _s(_get(["unit", "escalier"])),
        "floor": _s(_get(["floor", "etage"])),
        "house_no": _s(_get(["house no", "numero de maison"])),
        "additional_address_info": _s(_get(["additional address information", "complément d'adresse"])),
        "customer_full_name": _s(_get(["customer full name", "nom et prenom"])),
        "province": _s(_get(["province", "wilaya"])),
        "district": _s(_get(["district", "daira"])),
        "city": _s(_get(["city", "commune"])),
        "postal_code": _s(_get(["postal code", "code postal"])),
        "expiry_date": _d(_get(["expiry date", "expiration"])),
        "iccid": _s(_get(["iccid", "sim"])),
        "imsi": _s(_get(["imsi"])),
        "contact_number": _s(_get(["contact number", "numéro de contact"])),
        "created_at": datetime.utcnow(),
    }

    return park_dict


if __name__ == "__main__":
    print("PRK Column Mapping:")
    for prk_header, db_field in PRK_TO_DB_MAPPING.items():
        print(f"  {prk_header} -> {db_field}")

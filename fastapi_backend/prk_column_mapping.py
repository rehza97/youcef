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
    """Map a PRK record to Park dictionary format"""
    from datetime import datetime

    def safe_get(key, default=None):
        return record.get(key, default)

    def safe_string(value):
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    def safe_float(value):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return float(text.replace(',', '.'))
        except Exception:
            return None

    def safe_date(value):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        # Try pandas/ISO first; fallback to None if unparseable
        try:
            import pandas as pd
            return pd.to_datetime(text, errors='coerce', dayfirst=False).to_pydatetime()
        except Exception:
            return None

    park_dict = {
        'file_upload_id': file_upload_id,
        'extraction_date': safe_date(safe_get('Extraction Date_Date d ‘extraction')),
        'actel_code': safe_string(safe_get('Actel Code_Code d’actel')),
        'telecom_type': safe_string(safe_get('Telecom type_SERVICE / PRODUIT')),
        'offer_type': safe_string(safe_get('Offer Type_Type d’offre')),
        'offer_name': safe_string(safe_get('Offer name_Nom de l’offre')),
        'rental_fees': safe_float(safe_get('Rental Fees_Frais d’abonnement')),
        'customer_code': safe_string(safe_get('Customer code_NCLI')),
        'service_number': safe_string(safe_get('Service number_ND')),
        'related_service_number': safe_string(safe_get('Related Service Number_Numero de service correspondant')),
        'username': safe_string(safe_get('USERNAME_Nom d’utilisateur')),
        'subscriber_status': safe_string(safe_get('Subscriber status_Status de l’abonne')),
        'status_date': safe_date(safe_get('Status date_Date du statut')),
        'creation_date': safe_date(safe_get('Creation Date_Date de creation')),
        'active_date': safe_date(safe_get('Active Date_Date d'"+"'"+"activation')),
        'csr_name': safe_string(safe_get('CSR Name_Nom CSR')),
        'department_name': safe_string(safe_get('Department Name_Nom de département1')),
        'state': safe_string(safe_get('State_Wilaya')),
        'area': safe_string(safe_get('Area_Daira')),
        'town': safe_string(safe_get('Town_Commune')),
        'grid': safe_string(safe_get('Grid_Quartier')),
        'street': safe_string(safe_get('Street_Voie')),
        'street_number': safe_string(safe_get('Street Number_Numero De Voie')),
        'building_no': safe_string(safe_get('Building No._Batiment')),
        'unit': safe_string(safe_get('Unit_Escalier')),
        'floor': safe_string(safe_get('Floor_Etage')),
        'house_no': safe_string(safe_get('House No._Numero de maison')),
        'additional_address_info': safe_string(safe_get("Additional Address Information_Complément d'adresse")),
        'customer_full_name': safe_string(safe_get('Customer full name_NOM ET PRENOM')),
        'province': safe_string(safe_get('Province_Wilaya')),
        'district': safe_string(safe_get('District_Daira')),
        'city': safe_string(safe_get('City_Commune')),
        'postal_code': safe_string(safe_get('Postal Code_Code postal')),
        'expiry_date': safe_date(safe_get('Expiry Date_Date d’expiration')),
        'iccid': safe_string(safe_get('ICCID_N° SIM')),
        'imsi': safe_string(safe_get('IMSI_IMSI')),
        'contact_number': safe_string(safe_get('Contact number_Numéro de contact')),
        'created_at': datetime.utcnow()
    }

    return park_dict


if __name__ == "__main__":
    print("PRK Column Mapping:")
    for prk_header, db_field in PRK_TO_DB_MAPPING.items():
        print(f"  {prk_header} -> {db_field}")

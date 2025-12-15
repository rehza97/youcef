"""
Shared anomaly rules for Parc Corporate NGBSS.

Goal:
- By default, anomaly records must be excluded from visualizations, filters, and normal exports.
- Anomalies must still be retrievable for anomaly-only exports.

We support both:
1) A persisted flag (`is_anomaly`) when ETL sets it
2) A safety-net predicate (business rules) in case old/new rows are missing the flag
"""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import or_


ANOMALY_TELECOM_TYPES = ("WIFI", "WIMAX", "X25")
ANOMALY_CUSTOMER_L3_CODES = ("5", "57")


def normalize_customer_l3_code(value: object) -> Optional[str]:
    """Normalize customer_l3_code into '5'/'57'/... string when possible.

    Handles common Excel/CSV cases:
    - 5, 57
    - 5.0, 57.0
    - " 5 ", "57.0"
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    # Fast path: pure digits
    if s.isdigit():
        return s

    # Handle floats like "5.0" / "57.0"
    try:
        f = float(s)
        i = int(f)
        if f == i:
            return str(i)
    except Exception:
        pass

    return s


def detect_anomaly_fields(
    *,
    customer_l3_code: object,
    telecom_type: object,
    offer_name: object,
) -> Tuple[bool, Optional[str]]:
    """Pure python anomaly detection used during ingestion."""
    reasons = []

    l3 = normalize_customer_l3_code(customer_l3_code)
    if l3 in ANOMALY_CUSTOMER_L3_CODES:
        reasons.append(f"Code Customer L3: {l3}")

    if telecom_type is not None:
        t = str(telecom_type).strip().upper()
        if t in ANOMALY_TELECOM_TYPES:
            reasons.append(f"Telecom Type: {t}")

    if offer_name is not None:
        offer = str(offer_name).strip()
        if offer:
            offer_lower = offer.lower()
            if "moohtarif" in offer_lower:
                reasons.append("Offer name contains: Moohtarif")
            if "solutions" in offer_lower and ("hebergements" in offer_lower or "hébergements" in offer_lower):
                reasons.append("Offer name contains: Solutions Hebergements")

    if reasons:
        return True, "; ".join(reasons)
    return False, None


def sqlalchemy_anomaly_predicate(model):
    """SQLAlchemy predicate that matches anomaly rows (business rules)."""
    return or_(
        model.telecom_type.in_(ANOMALY_TELECOM_TYPES),
        model.customer_l3_code.in_(ANOMALY_CUSTOMER_L3_CODES),
        model.offer_name.ilike("%moohtarif%"),
        or_(
            model.offer_name.ilike("%Solutions Hébergement%"),
            model.offer_name.ilike("%Solutions Hebergement%"),
            model.offer_name.ilike("%solutions%hebergements%"),
            model.offer_name.ilike("%solutions%hébergements%"),
        ),
    )


def apply_default_anomaly_exclusion(query, model):
    """Exclude anomalies from a query (default for visualizations/filters/normal exports)."""
    pred = sqlalchemy_anomaly_predicate(model)

    # Primary: persisted flag when available
    if hasattr(model, "is_anomaly"):
        query = query.filter(model.is_anomaly.is_(False))

    # Safety net: exclude records matching rules even if flag wasn't set
    query = query.filter(~pred)
    return query


def apply_anomaly_only(query, model):
    """Include anomaly rows only (for anomaly export)."""
    pred = sqlalchemy_anomaly_predicate(model)
    if hasattr(model, "is_anomaly"):
        return query.filter(or_(model.is_anomaly.is_(True), pred))
    return query.filter(pred)





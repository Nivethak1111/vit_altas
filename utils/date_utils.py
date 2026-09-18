"""
Clinical Date and Time Utilities
Handles CDISC ISO 8601 formats, partial dates, and interval calculations.
"""
from datetime import datetime
from typing import Optional, Tuple


def parse_clinical_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str or not isinstance(date_str, str):
        return None
    s = date_str.strip()
    if not s or s.upper() in ("NA", "NULL", "NONE", "ND", ""):
        return None

    # Supported formats
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d%b%Y",
        "%Y-%m",
        "%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def days_between(start_str: Optional[str], end_str: Optional[str]) -> Optional[float]:
    d1 = parse_clinical_date(start_str)
    d2 = parse_clinical_date(end_str)
    if d1 is None or d2 is None:
        return None
    delta = d2 - d1
    return delta.total_seconds() / 86400.0


def hours_between(start_str: Optional[str], end_str: Optional[str]) -> Optional[float]:
    d1 = parse_clinical_date(start_str)
    d2 = parse_clinical_date(end_str)
    if d1 is None or d2 is None:
        return None
    delta = d2 - d1
    return delta.total_seconds() / 3600.0

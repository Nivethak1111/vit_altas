"""
Clinical Value Parser
Explicitly distinguishes:
- numeric result
- below detection (e.g. <5, <0.01)
- not done (e.g. ND, NOT DONE)
- missing (e.g. blank, NA, NULL)
Never converts non-numeric states into numeric zero!
"""
import re
from typing import Optional
from models.study_record import SpecialLabStatus, SpecialLabValue


def parse_lab_value(val_str: Optional[str]) -> SpecialLabValue:
    if val_str is None:
        return SpecialLabValue(raw_value="", status=SpecialLabStatus.MISSING, numeric_value=None)

    s = str(val_str).strip()
    if s == "" or s.upper() in ("NA", "NULL", "MISSING", ".", "-"):
        return SpecialLabValue(raw_value=s, status=SpecialLabStatus.MISSING, numeric_value=None)

    upper_s = s.upper()
    if upper_s in ("ND", "NOT DONE", "NOT_DONE", "N/D"):
        return SpecialLabValue(raw_value=s, status=SpecialLabStatus.NOT_DONE, numeric_value=None)

    # Below detection: e.g. <5, <=0.1, < 10
    below_match = re.match(r"^([<≤]|<=)\s*([0-9]+(?:\.[0-9]+)?)$", s)
    if below_match:
        comparator = below_match.group(1)
        limit_val = float(below_match.group(2))
        return SpecialLabValue(
            raw_value=s,
            status=SpecialLabStatus.BELOW_DETECTION,
            numeric_value=limit_val,
            comparator=comparator,
        )

    # Above detection: e.g. >1000
    above_match = re.match(r"^([>≥]|>=)\s*([0-9]+(?:\.[0-9]+)?)$", s)
    if above_match:
        comparator = above_match.group(1)
        limit_val = float(above_match.group(2))
        return SpecialLabValue(
            raw_value=s,
            status="ABOVE_DETECTION",
            numeric_value=limit_val,
            comparator=comparator,
        )

    # Standard numeric
    try:
        # Handle commas as decimal separator or thousands separator
        clean_num = s.replace(",", "")
        num = float(clean_num)
        return SpecialLabValue(
            raw_value=s,
            status=SpecialLabStatus.NUMERIC,
            numeric_value=num,
        )
    except ValueError:
        # Textual finding or other non-numeric status
        return SpecialLabValue(
            raw_value=s,
            status=SpecialLabStatus.NOT_DONE if "NOT" in upper_s else "TEXT",
            numeric_value=None,
        )

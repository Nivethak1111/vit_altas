"""
Clinical Unit Normalizer
Preserves original reported unit and value, and provides normalized values
for clinical rule and reference range evaluation.
Specifically supports: 1 µkat/L = 60 U/L for ALT/AST/ALP.
"""
from typing import Optional, Tuple


def normalize_unit_string(unit: Optional[str]) -> str:
    if not unit:
        return ""
    u = unit.strip()
    # Normalize micro signs
    u = u.replace("μ", "µ").replace("u", "µ")
    return u


def convert_lab_value(
    value: float,
    from_unit: str,
    to_unit: str,
    test_name: Optional[str] = None
) -> Tuple[Optional[float], bool]:
    """
    Converts a numeric value from from_unit to to_unit.
    Returns (converted_value, conversion_applied).
    """
    if value is None:
        return None, False

    u_from = normalize_unit_string(from_unit).lower()
    u_to = normalize_unit_string(to_unit).lower()

    if u_from == u_to:
        return value, False

    t_upper = (test_name or "").upper()

    # ALT, AST, ALP: µkat/L <-> U/L
    # 1 µkat/L = 60 U/L
    if ("kat" in u_from or "kat" in u_to) and ("u/l" in u_from or "u/l" in u_to or "iu/l" in u_from or "iu/l" in u_to):
        if ("µkat/l" in u_from or "ukat/l" in u_from) and ("u/l" in u_to or "iu/l" in u_to):
            return value * 60.0, True
        if ("u/l" in u_from or "iu/l" in u_from) and ("µkat/l" in u_to or "ukat/l" in u_to):
            return value / 60.0, True
        if "nkat/l" in u_from and ("u/l" in u_to or "iu/l" in u_to):
            return value * 0.06, True

    # Bilirubin: µmol/L <-> mg/dL (1 mg/dL = 17.1 µmol/L)
    if "bili" in t_upper or "tbil" in t_upper or "ibil" in t_upper or "dbil" in t_upper:
        if ("µmol/l" in u_from or "umol/l" in u_from) and "mg/dl" in u_to:
            return value / 17.1, True
        if "mg/dl" in u_from and ("µmol/l" in u_to or "umol/l" in u_to):
            return value * 17.1, True

    # Creatinine: µmol/L <-> mg/dL (1 mg/dL = 88.4 µmol/L)
    if "creat" in t_upper:
        if ("µmol/l" in u_from or "umol/l" in u_from) and "mg/dl" in u_to:
            return value / 88.4, True
        if "mg/dl" in u_from and ("µmol/l" in u_to or "umol/l" in u_to):
            return value * 88.4, True

    # Glucose: mmol/L <-> mg/dL (1 mmol/L = 18.0182 mg/dL)
    if "gluc" in t_upper:
        if "mmol/l" in u_from and "mg/dl" in u_to:
            return value * 18.0182, True
        if "mg/dl" in u_from and "mmol/l" in u_to:
            return value / 18.0182, True

    # Same prefix or unknown - return original without silent conversion
    return value, False

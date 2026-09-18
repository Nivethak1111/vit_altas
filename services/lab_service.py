"""
Laboratory Evaluation and Safety Service
Interprets laboratory records strictly using LAB + TEST specific reference ranges,
normalizes units when necessary, handles special values, and evaluates clinical flags.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from models.reference_range import LabReferenceRange
from models.study_record import DomainRecord, SpecialLabStatus, SpecialLabValue
from rules.unit_normalizer import convert_lab_value
from rules.value_parser import parse_lab_value


@dataclass
class LabInterpretation:
    lab: str
    test: str
    raw_value: str
    special_status: str
    numeric_value: Optional[float]
    reported_unit: str
    normalized_value: Optional[float]
    normalized_unit: str
    unit_conversion_applied: bool
    ref_low: Optional[float]
    ref_high: Optional[float]
    ref_unit: str
    elevation_ratio: Optional[float]  # value / ULN (or value / high)
    interpretation: str  # NORMAL, HIGH, LOW, BELOW_DETECTION, NOT_DONE, MISSING, UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lab": self.lab,
            "test": self.test,
            "raw_value": self.raw_value,
            "special_status": self.special_status,
            "numeric_value": self.numeric_value,
            "reported_unit": self.reported_unit,
            "normalized_value": self.normalized_value,
            "normalized_unit": self.normalized_unit,
            "unit_conversion_applied": self.unit_conversion_applied,
            "ref_low": self.ref_low,
            "ref_high": self.ref_high,
            "ref_unit": self.ref_unit,
            "elevation_ratio": round(self.elevation_ratio, 2) if self.elevation_ratio is not None else None,
            "interpretation": self.interpretation,
        }


class LabSafetyService:
    def __init__(self, reference_ranges: Optional[List[LabReferenceRange]] = None):
        # Key: (lab.upper().strip(), test.upper().strip())
        self._ranges: Dict[Tuple[str, str], LabReferenceRange] = {}
        if reference_ranges:
            for rr in reference_ranges:
                self.add_reference_range(rr)

    def add_reference_range(self, rr: LabReferenceRange):
        key = (rr.lab.upper().strip(), rr.test.upper().strip())
        self._ranges[key] = rr

    SYNONYMS: Dict[str, List[str]] = {
        "ALT": ["ALANINE AMINOTRANSFERASE", "SGPT", "ALT"],
        "AST": ["ASPARTATE AMINOTRANSFERASE", "SGOT", "AST"],
        "TBIL": ["TOTAL BILIRUBIN", "BILIRUBIN", "TBIL"],
        "ALP": ["ALKALINE PHOSPHATASE", "ALP"],
        "CREATININE": ["CREATININE", "CREAT"],
        "HBA1C": ["HEMOGLOBIN A1C", "HBA1C", "A1C"],
    }

    def get_reference_range(self, lab: str, test: str) -> Optional[LabReferenceRange]:
        lab_clean = (lab or "").upper().strip()
        test_clean = (test or "").upper().strip()

        # Build list of potential test names (including synonyms)
        test_variants = [test_clean]
        for canonical, syns in self.SYNONYMS.items():
            if test_clean in syns or test_clean == canonical:
                for s in syns:
                    if s not in test_variants:
                        test_variants.append(s)

        # 1. Exact match by (LAB, variant)
        for t_var in test_variants:
            if (lab_clean, t_var) in self._ranges:
                return self._ranges[(lab_clean, t_var)]

        # 2. Lab-specific partial match
        for (l, t), rr in self._ranges.items():
            if l == lab_clean and (t in test_variants or any(v in t for v in test_variants)):
                return rr

        # 3. Fallback to CENTRAL LAB or any lab with this test
        for t_var in test_variants:
            for (l, t), rr in self._ranges.items():
                if t == t_var and ("CENTRAL" in l or not lab_clean):
                    return rr

        for (l, t), rr in self._ranges.items():
            if t in test_variants or any(v in t for v in test_variants):
                return rr

        return None

    def evaluate_record(self, record: DomainRecord) -> LabInterpretation:
        """
        Takes a laboratory DomainRecord (e.g. from LB domain), extracts clinical fields,
        resolves lab+test range, performs unit normalization, and returns structured interpretation.
        """
        test_cd = (record.get("LBTESTCD") or "").strip()
        test_name = (record.get("LBTEST") or record.get("TEST") or "").strip()
        test = test_cd if test_cd else test_name
        lab = record.get("LBNAM") or record.get("LAB") or record.get("LABNAM") or "CENTRAL LAB"
        raw_val = str(record.get("LBORRES") or record.get("RESULT") or "")
        reported_unit = str(record.get("LBORRESU") or record.get("UNIT") or "")

        parsed_val = parse_lab_value(raw_val)

        # Lookup LAB + TEST range (try test_cd then test_name)
        rr = self.get_reference_range(lab, test_cd) if test_cd else None
        if not rr:
            rr = self.get_reference_range(lab, test_name)
        if not rr and test:
            rr = self.get_reference_range(lab, test)

        ref_low = rr.low if rr else None
        ref_high = rr.high if rr else None
        ref_unit = rr.unit if rr else reported_unit

        if parsed_val.status != SpecialLabStatus.NUMERIC:
            return LabInterpretation(
                lab=lab,
                test=test,
                raw_value=raw_val,
                special_status=parsed_val.status,
                numeric_value=None,
                reported_unit=reported_unit,
                normalized_value=None,
                normalized_unit=reported_unit,
                unit_conversion_applied=False,
                ref_low=ref_low,
                ref_high=ref_high,
                ref_unit=ref_unit,
                elevation_ratio=None,
                interpretation=parsed_val.status,
            )

        # Normalization if unit differs from reference range unit
        num_val = parsed_val.numeric_value
        norm_val, conv_applied = convert_lab_value(num_val, reported_unit, ref_unit, test)
        eval_val = norm_val if norm_val is not None else num_val

        # Evaluate against limits
        interpretation = "NORMAL"
        elevation_ratio = None
        if ref_high is not None and ref_high > 0:
            elevation_ratio = eval_val / ref_high
            if eval_val > ref_high:
                interpretation = "HIGH"
        if ref_low is not None and eval_val < ref_low:
            interpretation = "LOW"

        return LabInterpretation(
            lab=lab,
            test=test,
            raw_value=raw_val,
            special_status=SpecialLabStatus.NUMERIC,
            numeric_value=num_val,
            reported_unit=reported_unit,
            normalized_value=eval_val,
            normalized_unit=ref_unit if conv_applied else reported_unit,
            unit_conversion_applied=conv_applied,
            ref_low=ref_low,
            ref_high=ref_high,
            ref_unit=ref_unit,
            elevation_ratio=elevation_ratio,
            interpretation=interpretation,
        )

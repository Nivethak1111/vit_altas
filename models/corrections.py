"""
Correction models for historical audit-trail tracking
"""
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class FieldCorrection:
    domain: str
    usubjid: str
    seq: int
    field_name: str
    original_value: str
    corrected_value: str
    correction_cut: int
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "usubjid": self.usubjid,
            "seq": self.seq,
            "field_name": self.field_name,
            "original_value": self.original_value,
            "corrected_value": self.corrected_value,
            "correction_cut": self.correction_cut,
            "reason": self.reason,
        }

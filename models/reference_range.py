"""
Laboratory Reference Range and Unit Conversion Models
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LabReferenceRange:
    lab: str
    test: str
    unit: str
    low: Optional[float] = None
    high: Optional[float] = None
    sex: Optional[str] = None
    age_low: Optional[float] = None
    age_high: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lab": self.lab,
            "test": self.test,
            "unit": self.unit,
            "low": self.low,
            "high": self.high,
            "sex": self.sex,
            "age_low": self.age_low,
            "age_high": self.age_high,
        }

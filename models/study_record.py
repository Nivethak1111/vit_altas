"""
Core Data Models: Evidence Identity, Domain Record, and Special Lab Values
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class SpecialLabStatus:
    NUMERIC = "NUMERIC"
    BELOW_DETECTION = "BELOW_DETECTION"
    NOT_DONE = "NOT_DONE"
    MISSING = "MISSING"


@dataclass
class SpecialLabValue:
    raw_value: str
    status: str
    numeric_value: Optional[float] = None
    comparator: Optional[str] = None  # e.g. "<" for "<5"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_value": self.raw_value,
            "status": self.status,
            "numeric_value": self.numeric_value,
            "comparator": self.comparator,
        }


@dataclass(frozen=True)
class EvidenceIdentity:
    domain: str
    usubjid: str
    seq: int

    @property
    def key(self) -> str:
        return f"{self.domain}|{self.usubjid}|{self.seq}"

    def to_tuple(self) -> Tuple[str, str, int]:
        return (self.domain, self.usubjid, self.seq)

    def __str__(self) -> str:
        return self.key


@dataclass
class DomainRecord:
    domain: str
    usubjid: str
    seq: int
    cut_available: int
    corrected_at_cut: Optional[int] = None
    original_fields: Dict[str, Any] = field(default_factory=dict)
    current_fields: Dict[str, Any] = field(default_factory=dict)
    is_corrected: bool = False
    correction_history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def identity(self) -> EvidenceIdentity:
        return EvidenceIdentity(domain=self.domain, usubjid=self.usubjid, seq=self.seq)

    def get(self, key: str, default: Any = None) -> Any:
        return self.current_fields.get(key, self.original_fields.get(key, default))

    def get_original(self, key: str, default: Any = None) -> Any:
        return self.original_fields.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "usubjid": self.usubjid,
            "seq": self.seq,
            "cut_available": self.cut_available,
            "corrected_at_cut": self.corrected_at_cut,
            "is_corrected": self.is_corrected,
            "identity": str(self.identity),
            "fields": dict(self.current_fields),
            "original_fields": dict(self.original_fields),
            "correction_history": self.correction_history,
        }

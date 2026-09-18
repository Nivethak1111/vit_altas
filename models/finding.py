"""
Clinical Monitoring Finding Model
Traceable to exact evidence tuples: (domain, USUBJID, SEQ)
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class FindingSeverity:
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MODERATE = "MODERATE"
    MINOR = "MINOR"
    INFO = "INFO"


class FindingStatus:
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


@dataclass
class Finding:
    finding_code: str
    subject: str
    site: str
    domain: str
    description: str
    protocol_version: str
    data_cut: int
    severity: str = FindingSeverity.MAJOR
    status: str = FindingStatus.OPEN
    evidence_references: List[str] = field(default_factory=list)  # ["DOMAIN|USUBJID|SEQ"]
    supporting_records: List[Dict[str, Any]] = field(default_factory=list)
    site_reply: Optional[Dict[str, Any]] = None
    monitor_decision: Optional[Dict[str, Any]] = None
    rule_name: str = ""
    discrepancy_details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_code": self.finding_code,
            "subject": self.subject,
            "site": self.site,
            "domain": self.domain,
            "description": self.description,
            "protocol_version": self.protocol_version,
            "data_cut": self.data_cut,
            "severity": self.severity,
            "status": self.status,
            "evidence_references": self.evidence_references,
            "supporting_records": self.supporting_records,
            "site_reply": self.site_reply,
            "monitor_decision": self.monitor_decision,
            "rule_name": self.rule_name,
            "discrepancy_details": self.discrepancy_details,
        }

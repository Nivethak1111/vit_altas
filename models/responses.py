"""
External Response and Validation Data Models
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional


class MonitorDecisionStatus:
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLARIFY = "CLARIFY"


@dataclass
class SiteReply:
    domain: str
    usubjid: str
    seq: int
    reply: str
    is_default: bool = False
    query_text: Optional[str] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "usubjid": self.usubjid,
            "seq": self.seq,
            "reply": self.reply,
            "is_default": self.is_default,
            "query_text": self.query_text,
            "timestamp": self.timestamp,
        }


@dataclass
class MonitorDecision:
    code: str
    usubjid: str
    decision: str  # APPROVED, REJECTED, CLARIFY
    inquiry: Optional[str] = None  # Request for additional info if CLARIFY
    comment: Optional[str] = None
    monitor_name: Optional[str] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "usubjid": self.usubjid,
            "decision": self.decision,
            "inquiry": self.inquiry,
            "comment": self.comment,
            "monitor_name": self.monitor_name,
            "timestamp": self.timestamp,
        }

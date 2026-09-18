"""
Response and Validation Service
Manages external Site Replies (DOMAIN|USUBJID|SEQ with _default fallback)
and Monitor Decisions (CODE|USUBJID supporting APPROVED, REJECTED, CLARIFY).
"""
from typing import Any, Dict, Optional
from models.responses import MonitorDecision, MonitorDecisionStatus, SiteReply


class ResponseService:
    def __init__(
        self,
        site_replies_raw: Optional[Dict[str, Any]] = None,
        monitor_decisions_raw: Optional[Dict[str, Any]] = None,
    ):
        self._site_replies: Dict[str, Any] = site_replies_raw or {}
        self._monitor_decisions: Dict[str, Any] = monitor_decisions_raw or {}

    def get_site_reply(self, domain: str, usubjid: str, seq: int) -> Dict[str, Any]:
        """
        Lookup exact reply by DOMAIN|USUBJID|SEQ.
        If not found, fall back to '_default'.
        """
        key = f"{domain.upper().strip()}|{str(usubjid).strip()}|{int(seq)}"
        if key in self._site_replies:
            val = self._site_replies[key]
            if isinstance(val, dict):
                return {
                    "domain": domain,
                    "usubjid": usubjid,
                    "seq": seq,
                    "reply": val.get("reply", str(val)),
                    "query_text": val.get("query_text", ""),
                    "timestamp": val.get("timestamp", ""),
                    "is_default": False,
                }
            return {
                "domain": domain,
                "usubjid": usubjid,
                "seq": seq,
                "reply": str(val),
                "is_default": False,
            }

        # Fallback to _default
        default_val = self._site_replies.get("_default")
        if default_val is not None:
            if isinstance(default_val, dict):
                return {
                    "domain": domain,
                    "usubjid": usubjid,
                    "seq": seq,
                    "reply": default_val.get("reply", str(default_val)),
                    "is_default": True,
                }
            return {
                "domain": domain,
                "usubjid": usubjid,
                "seq": seq,
                "reply": str(default_val),
                "is_default": True,
            }

        return {
            "domain": domain,
            "usubjid": usubjid,
            "seq": seq,
            "reply": "No site reply on file.",
            "is_default": True,
        }

    def get_monitor_decision(self, code: str, usubjid: str) -> Optional[Dict[str, Any]]:
        """
        Lookup monitor decision by CODE|USUBJID.
        Supports: APPROVED, REJECTED, CLARIFY.
        For CLARIFY, includes inquiry/request for additional info.
        """
        key = f"{code.upper().strip()}|{str(usubjid).strip()}"
        if key in self._monitor_decisions:
            item = self._monitor_decisions[key]
            if isinstance(item, dict):
                decision_str = str(item.get("decision", "")).upper()
                return {
                    "code": code,
                    "usubjid": usubjid,
                    "decision": decision_str,
                    "inquiry": item.get("inquiry", item.get("question", None)),
                    "comment": item.get("comment", ""),
                    "monitor_name": item.get("monitor_name", "Clinical Monitor"),
                    "timestamp": item.get("timestamp", ""),
                }
            decision_str = str(item).upper()
            return {
                "code": code,
                "usubjid": usubjid,
                "decision": decision_str,
                "inquiry": None,
                "comment": "",
                "monitor_name": "Clinical Monitor",
                "timestamp": "",
            }

        # Also check without subject (e.g. code-level decision if any)
        code_only_key = code.upper().strip()
        if code_only_key in self._monitor_decisions:
            item = self._monitor_decisions[code_only_key]
            if isinstance(item, dict):
                return {
                    "code": code,
                    "usubjid": usubjid,
                    "decision": str(item.get("decision", "")).upper(),
                    "inquiry": item.get("inquiry"),
                    "comment": item.get("comment", ""),
                    "monitor_name": item.get("monitor_name", "Clinical Monitor"),
                    "timestamp": item.get("timestamp", ""),
                }

        return None

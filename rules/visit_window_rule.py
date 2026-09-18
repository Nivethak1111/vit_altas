"""
Protocol-Aware Visit Window Evaluation Rule
Protocol v1: Window is ±7 days
Protocol v2/v3: Window is ±3 days
Dynamically checks the protocol version active at the requested data cut.
"""
import re
from typing import Any, Dict, List, Optional
from models.finding import Finding, FindingSeverity, FindingStatus
from models.graph_nodes import SubjectNode
from rules.base_rule import BaseClinicalRule
from utils.date_utils import days_between


# Standard target days by visit name
TARGET_VISIT_DAYS: Dict[str, int] = {
    "SCREENING": -14,
    "BASELINE": 1,
    "DAY 1": 1,
    "VISIT 1": 1,
    "WEEK 2": 14,
    "VISIT 2": 14,
    "WEEK 4": 28,
    "VISIT 3": 28,
    "WEEK 8": 56,
    "VISIT 4": 56,
    "WEEK 12": 84,
    "VISIT 5": 84,
    "WEEK 16": 112,
    "VISIT 6": 112,
    "WEEK 24": 168,
    "VISIT 7": 168,
}


def parse_target_day_from_visit(visit_name: str) -> Optional[int]:
    v_clean = visit_name.upper().strip()
    for k, day in TARGET_VISIT_DAYS.items():
        if k in v_clean:
            return day

    # Check e.g. "WEEK X" -> X * 7
    week_match = re.search(r"WEEK\s*(\d+)", v_clean)
    if week_match:
        return int(week_match.group(1)) * 7

    # Check e.g. "DAY X" -> X
    day_match = re.search(r"DAY\s*(\d+)", v_clean)
    if day_match:
        return int(day_match.group(1))

    return None


class VisitWindowRule(BaseClinicalRule):
    rule_name: str = "Visit Window Protocol Compliance"
    rule_code: str = "VISIT_WINDOW_DEVIATION"

    def evaluate(self, subject: SubjectNode, graph: Any, cut: int) -> List[Finding]:
        findings = []
        protocol_version = str(graph.get_protocol_for_cut(cut)).lower()

        # Window rule dynamically based on protocol version
        if "v1" in protocol_version:
            allowed_window_days = 7
        else:
            # Protocol v2 and v3
            allowed_window_days = 3

        # Reference start date from DM (RFSTDTC)
        rfstdtc = None
        if subject.demographics:
            rfstdtc = subject.demographics.get("RFSTDTC") or subject.demographics.get("RFSTDAT")

        if not rfstdtc:
            return findings

        # Check visits in VS records
        vs_records = subject.get_vital_signs(cut)
        checked_visits = set()

        for vs in vs_records:
            visit = str(vs.get("VISIT", "")).strip().upper()
            vsdate = vs.get("VSDTC") or vs.get("VSDAT") or vs.get("DATE")

            if not visit or not vsdate or visit in checked_visits:
                continue

            target_day = parse_target_day_from_visit(visit)
            if target_day is None or target_day <= 1:
                # Skip baseline / Day 1 / Screening
                continue

            actual_diff_days = days_between(rfstdtc, vsdate)
            if actual_diff_days is None:
                continue

            actual_study_day = int(actual_diff_days) + 1  # Day 1 is baseline
            deviation = actual_study_day - target_day
            checked_visits.add(visit)

            if abs(deviation) > allowed_window_days:
                sign = "+" if deviation > 0 else ""
                finding = Finding(
                    finding_code="VISIT_WINDOW_DEVIATION",
                    subject=subject.usubjid,
                    site=subject.site_id,
                    domain="VS",
                    severity=FindingSeverity.MODERATE,
                    status=FindingStatus.OPEN,
                    description=(
                        f"Visit Window Out-of-Range: {visit} occurred on Study Day {actual_study_day} "
                        f"({sign}{deviation} days from target Day {target_day}). Active {protocol_version.upper()} "
                        f"allows ±{allowed_window_days} days."
                    ),
                    protocol_version=protocol_version,
                    data_cut=cut,
                    evidence_references=[str(vs.identity)],
                    supporting_records=[vs.to_dict()],
                    rule_name=self.rule_name,
                    discrepancy_details={
                        "visit": visit,
                        "target_day": target_day,
                        "actual_study_day": actual_study_day,
                        "deviation_days": deviation,
                        "allowed_window": allowed_window_days,
                    },
                )
                reply = graph.get_site_reply("VS", subject.usubjid, vs.seq)
                if reply:
                    finding.site_reply = reply
                decision = graph.get_monitor_decision("VISIT_WINDOW_DEVIATION", subject.usubjid)
                if decision:
                    finding.monitor_decision = decision
                findings.append(finding)

        return findings

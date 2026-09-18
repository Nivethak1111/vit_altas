"""
Prohibited Medications Evaluation Rule
Evaluates CM.csv and CMCLAS:
- Protocol v1/v2: Prohibits systemic glucocorticoids.
- Protocol v3: Prohibits systemic glucocorticoids AND Sulfonylureas.
Dynamically resolves active protocol version for the cut.
"""
from typing import Any, List
from models.finding import Finding, FindingSeverity, FindingStatus
from models.graph_nodes import SubjectNode
from rules.base_rule import BaseClinicalRule


GLUCOCORTICOID_KEYWORDS = [
    "GLUCOCORTICOID",
    "CORTICOSTEROID",
    "PREDNISONE",
    "PREDNISOLONE",
    "DEXAMETHASONE",
    "METHYLPREDNISOLONE",
    "HYDROCORTISONE",
    "TRIAMCINOLONE",
    "BETAMETHASONE",
]

SULFONYLUREA_KEYWORDS = [
    "SULFONYLUREA",
    "SULPHONYLUREA",
    "GLIMEPIRIDE",
    "GLIPIZIDE",
    "GLIBENCLAMIDE",
    "GLYBURIDE",
    "GLICLAZIDE",
    "GLICLAZID",
]


class ProhibitedMedicationsRule(BaseClinicalRule):
    rule_name: str = "Prohibited Concomitant Medication"
    rule_code: str = "PROHIBITED_MED"

    def evaluate(self, subject: SubjectNode, graph: Any, cut: int) -> List[Finding]:
        findings = []
        protocol_version = str(graph.get_protocol_for_cut(cut)).lower()

        cm_records = subject.get_medications(cut)
        for cm in cm_records:
            cmtrt = str(cm.get("CMTRT", "")).strip().upper()
            cmclas = str(cm.get("CMCLAS", "")).strip().upper()
            start_date = cm.get("CMSTDTC") or cm.get("CMSTDAT") or "Not documented"
            end_date = cm.get("CMENDTC") or cm.get("CMENDAT") or "Ongoing"

            # 1. Systemic Glucocorticoids (Prohibited in all protocol versions)
            is_gluco = any(k in cmclas or k in cmtrt for k in GLUCOCORTICOID_KEYWORDS)
            if is_gluco:
                finding = Finding(
                    finding_code="PROHIBITED_MED_GLUCOCORTICOID",
                    subject=subject.usubjid,
                    site=subject.site_id,
                    domain="CM",
                    severity=FindingSeverity.CRITICAL,
                    status=FindingStatus.OPEN,
                    description=(
                        f"Prohibited Concomitant Medication: '{cmtrt}' (Class: '{cmclas}') "
                        f"is a systemic glucocorticoid prohibited under Protocol {protocol_version.upper()}."
                    ),
                    protocol_version=protocol_version,
                    data_cut=cut,
                    evidence_references=[str(cm.identity)],
                    supporting_records=[cm.to_dict()],
                    rule_name=self.rule_name,
                    discrepancy_details={
                        "medication": cmtrt,
                        "class": cmclas,
                        "start_date": start_date,
                        "end_date": end_date,
                        "prohibited_by": "Protocol v1/v2/v3",
                    },
                )
                reply = graph.get_site_reply("CM", subject.usubjid, cm.seq)
                if reply:
                    finding.site_reply = reply
                decision = graph.get_monitor_decision("PROHIBITED_MED_GLUCOCORTICOID", subject.usubjid)
                if decision:
                    finding.monitor_decision = decision
                findings.append(finding)

            # 2. Sulfonylurea (Additionally prohibited under Protocol v3)
            if "v3" in protocol_version:
                is_sulf = any(k in cmclas or k in cmtrt for k in SULFONYLUREA_KEYWORDS)
                if is_sulf:
                    finding = Finding(
                        finding_code="PROHIBITED_MED_SULFONYLUREA",
                        subject=subject.usubjid,
                        site=subject.site_id,
                        domain="CM",
                        severity=FindingSeverity.CRITICAL,
                        status=FindingStatus.OPEN,
                        description=(
                            f"Prohibited Concomitant Medication: '{cmtrt}' (Class: '{cmclas}') "
                            f"is a sulfonylurea newly prohibited under Amendment {protocol_version.upper()}."
                        ),
                        protocol_version=protocol_version,
                        data_cut=cut,
                        evidence_references=[str(cm.identity)],
                        supporting_records=[cm.to_dict()],
                        rule_name=self.rule_name,
                        discrepancy_details={
                            "medication": cmtrt,
                            "class": cmclas,
                            "start_date": start_date,
                            "end_date": end_date,
                            "prohibited_by": "Protocol v3 Amendment",
                        },
                    )
                    reply = graph.get_site_reply("CM", subject.usubjid, cm.seq)
                    if reply:
                        finding.site_reply = reply
                    decision = graph.get_monitor_decision("PROHIBITED_MED_SULFONYLUREA", subject.usubjid)
                    if decision:
                        finding.monitor_decision = decision
                    findings.append(finding)

        return findings

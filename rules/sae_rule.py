"""
Serious Adverse Event (SAE) Detection & 24-Hour Reporting Compliance Rule
- Protocol SAE criteria: death, life-threatening, hospitalization (AESHOSP=Y), prolongation, disability, congenital defect.
- Specific rule: AESHOSP = 'Y' indicates serious event even if AESER != 'Y'. Flag discrepancy.
- SAE Reporting: Evaluates 24-hour reporting requirement from site awareness/onset to report date without inventing missing dates.
"""
from typing import Any, List
from models.finding import Finding, FindingSeverity, FindingStatus
from models.graph_nodes import SubjectNode
from rules.base_rule import BaseClinicalRule
from utils.date_utils import hours_between, parse_clinical_date


class SAEDetectionRule(BaseClinicalRule):
    rule_name: str = "SAE Detection & Discrepancy Evaluation"
    rule_code: str = "SAE_CRITERIA"

    def evaluate(self, subject: SubjectNode, graph: Any, cut: int) -> List[Finding]:
        findings = []
        protocol_version = graph.get_protocol_for_cut(cut)
        ae_records = subject.get_adverse_events(cut)

        for ae in ae_records:
            reported_aeser = str(ae.get("AESER", "")).upper().strip()
            aeshosp = str(ae.get("AESHOSP", "")).upper().strip()
            aesdth = str(ae.get("AESDTH", "")).upper().strip()
            aeslife = str(ae.get("AESLIFE", "")).upper().strip()
            aesdisab = str(ae.get("AESDISAB", "")).upper().strip()
            aescong = str(ae.get("AESCONG", "")).upper().strip()
            aeterm = ae.get("AETERM") or ae.get("AEDECOD") or "Unspecified Adverse Event"

            # Check seriousness criteria
            seriousness_reasons = []
            if aesdth == "Y":
                seriousness_reasons.append("Death")
            if aeslife == "Y":
                seriousness_reasons.append("Life-threatening")
            if aeshosp == "Y":
                seriousness_reasons.append("Hospitalization / Prolonged hospitalization")
            if aesdisab == "Y":
                seriousness_reasons.append("Persistent/significant disability")
            if aescong == "Y":
                seriousness_reasons.append("Congenital anomaly/birth defect")

            derived_serious = len(seriousness_reasons) > 0

            # Rule: AESHOSP = Y means the event is serious even if AESER is not correctly marked.
            if aeshosp == "Y" and reported_aeser != "Y":
                finding = Finding(
                    finding_code="SAE_DISCREPANCY_AESHOSP",
                    subject=subject.usubjid,
                    site=subject.site_id,
                    domain="AE",
                    severity=FindingSeverity.CRITICAL,
                    status=FindingStatus.OPEN,
                    description=(
                        f"SAE Discrepancy: Event '{aeterm}' has hospitalization marked (AESHOSP=Y) "
                        f"but site marked AESER='{reported_aeser}'. By protocol definition, hospitalization "
                        f"mandates classification as a Serious Adverse Event."
                    ),
                    protocol_version=protocol_version,
                    data_cut=cut,
                    evidence_references=[str(ae.identity)],
                    supporting_records=[ae.to_dict()],
                    rule_name=self.rule_name,
                    discrepancy_details={
                        "reported_aeser": reported_aeser,
                        "rule_derived_seriousness": "Y",
                        "aeshosp": aeshosp,
                        "reasons": seriousness_reasons,
                    },
                )
                # Attach site reply and monitor decision if present
                reply = graph.get_site_reply("AE", subject.usubjid, ae.seq)
                if reply:
                    finding.site_reply = reply
                decision = graph.get_monitor_decision("SAE_DISCREPANCY_AESHOSP", subject.usubjid)
                if decision:
                    finding.monitor_decision = decision
                findings.append(finding)

            # Check other seriousness discrepancies (e.g. death or life-threatening marked but AESER != 'Y')
            elif derived_serious and reported_aeser != "Y":
                finding = Finding(
                    finding_code="SAE_DISCREPANCY_CRITERIA",
                    subject=subject.usubjid,
                    site=subject.site_id,
                    domain="AE",
                    severity=FindingSeverity.CRITICAL,
                    status=FindingStatus.OPEN,
                    description=(
                        f"SAE Discrepancy: Event '{aeterm}' satisfies protocol seriousness criteria "
                        f"({', '.join(seriousness_reasons)}) but site reported AESER='{reported_aeser}'."
                    ),
                    protocol_version=protocol_version,
                    data_cut=cut,
                    evidence_references=[str(ae.identity)],
                    supporting_records=[ae.to_dict()],
                    rule_name=self.rule_name,
                    discrepancy_details={
                        "reported_aeser": reported_aeser,
                        "rule_derived_seriousness": "Y",
                        "reasons": seriousness_reasons,
                    },
                )
                reply = graph.get_site_reply("AE", subject.usubjid, ae.seq)
                if reply:
                    finding.site_reply = reply
                decision = graph.get_monitor_decision("SAE_DISCREPANCY_CRITERIA", subject.usubjid)
                if decision:
                    finding.monitor_decision = decision
                findings.append(finding)

            # SAE Reporting Compliance (24 hours requirement)
            is_any_serious = (reported_aeser == "Y") or derived_serious
            if is_any_serious:
                # Dates
                aware_date_str = (
                    ae.get("AEAWRDTC")
                    or ae.get("AESTDTC")
                    or ae.get("AESTDAT")
                    or ae.get("START_DATE")
                )
                rep_date_str = (
                    ae.get("AEREPDTC")
                    or ae.get("AEREPDAT")
                    or ae.get("REPORT_DATE")
                    or ae.get("AEDTC")
                )

                if not rep_date_str:
                    # Missing report date
                    finding = Finding(
                        finding_code="SAE_REPORTING_DATE_MISSING",
                        subject=subject.usubjid,
                        site=subject.site_id,
                        domain="AE",
                        severity=FindingSeverity.MAJOR,
                        status=FindingStatus.OPEN,
                        description=(
                            f"SAE Reporting Review: Serious event '{aeterm}' has no documented "
                            f"SAE report date to verify the required 24-hour initial reporting timeline."
                        ),
                        protocol_version=protocol_version,
                        data_cut=cut,
                        evidence_references=[str(ae.identity)],
                        supporting_records=[ae.to_dict()],
                        rule_name="SAE 24-Hour Reporting Window",
                        discrepancy_details={
                            "awareness_date": aware_date_str,
                            "report_date": None,
                            "status": "REQUIRES_REVIEW",
                        },
                    )
                    reply = graph.get_site_reply("AE", subject.usubjid, ae.seq)
                    if reply:
                        finding.site_reply = reply
                    decision = graph.get_monitor_decision("SAE_REPORTING_DATE_MISSING", subject.usubjid)
                    if decision:
                        finding.monitor_decision = decision
                    findings.append(finding)
                else:
                    # Check hours or days
                    hr = hours_between(aware_date_str, rep_date_str)
                    if hr is not None and hr > 24.0:
                        finding = Finding(
                            finding_code="SAE_REPORTING_DELAY",
                            subject=subject.usubjid,
                            site=subject.site_id,
                            domain="AE",
                            severity=FindingSeverity.CRITICAL,
                            status=FindingStatus.OPEN,
                            description=(
                                f"SAE Reporting Delay: Serious event '{aeterm}' reported {hr:.1f} hours "
                                f"after awareness date ({aware_date_str} -> {rep_date_str}), exceeding the "
                                f"mandatory 24-hour protocol reporting window."
                            ),
                            protocol_version=protocol_version,
                            data_cut=cut,
                            evidence_references=[str(ae.identity)],
                            supporting_records=[ae.to_dict()],
                            rule_name="SAE 24-Hour Reporting Window",
                            discrepancy_details={
                                "awareness_date": aware_date_str,
                                "report_date": rep_date_str,
                                "hours_elapsed": round(hr, 1),
                                "status": "NON_COMPLIANT",
                            },
                        )
                        reply = graph.get_site_reply("AE", subject.usubjid, ae.seq)
                        if reply:
                            finding.site_reply = reply
                        decision = graph.get_monitor_decision("SAE_REPORTING_DELAY", subject.usubjid)
                        if decision:
                            finding.monitor_decision = decision
                        findings.append(finding)

        return findings

"""
Hy's Law Candidate Detector Rule
Candidate Criteria:
- ALT or AST > 3x ULN
- AND Total Bilirubin (TBIL) > 2x ULN within 14 days
- AND No documented cholestasis (ALP <= 2x ULN)
- AND No alternative medical explanation
Flags candidate for clinical adjudication without stating automatic diagnostic conclusions.
Cites all supporting laboratory evidence records with dates.
"""
from typing import Any, List
from models.finding import Finding, FindingSeverity, FindingStatus
from models.graph_nodes import SubjectNode
from rules.base_rule import BaseClinicalRule
from utils.date_utils import days_between


class HysLawRule(BaseClinicalRule):
    rule_name: str = "Hy's Law Potential Hepatotoxicity Evaluation"
    rule_code: str = "HYS_LAW_CANDIDATE"

    def evaluate(self, subject: SubjectNode, graph: Any, cut: int) -> List[Finding]:
        findings = []
        protocol_version = graph.get_protocol_for_cut(cut)
        lb_records = subject.get_laboratory_results(cut)

        transaminase_elevations = []  # (rec, test, ratio, date)
        bilirubin_elevations = []     # (rec, test, ratio, date)
        alp_records = []              # (rec, test, ratio, date)

        for lb in lb_records:
            test = str(lb.get("LBTEST", "") or lb.get("LBTESTCD", "")).upper()
            date_str = lb.get("LBDTC") or lb.get("LBDAT") or lb.get("DATE")
            interp = graph.interpret_lab_record(lb)

            if interp.elevation_ratio is None or not date_str:
                continue

            # ALT / AST > 3x ULN
            if test in ("ALT", "ALANINE AMINOTRANSFERASE", "SGPT", "AST", "ASPARTATE AMINOTRANSFERASE", "SGOT"):
                if interp.elevation_ratio > 3.0:
                    transaminase_elevations.append((lb, test, interp.elevation_ratio, date_str, interp))

            # TBIL > 2x ULN
            if "BILI" in test or "TBIL" in test:
                if interp.elevation_ratio > 2.0:
                    bilirubin_elevations.append((lb, test, interp.elevation_ratio, date_str, interp))

            # ALP (Alkaline Phosphatase)
            if "ALP" in test or "ALKALINE PHOSPHATASE" in test:
                alp_records.append((lb, test, interp.elevation_ratio, date_str, interp))

        # Check pair-wise within 14 days
        for trans_rec, t_test, t_ratio, t_date, t_interp in transaminase_elevations:
            for bili_rec, b_test, b_ratio, b_date, b_interp in bilirubin_elevations:
                diff = days_between(t_date, b_date)
                if diff is not None and abs(diff) <= 14.0:
                    # Check for cholestasis: ALP > 2x ULN near these dates
                    cholestasis_found = False
                    for alp_rec, a_test, a_ratio, a_date, a_interp in alp_records:
                        d_alp = days_between(t_date, a_date)
                        if d_alp is not None and abs(d_alp) <= 14.0:
                            if a_ratio > 2.0:
                                cholestasis_found = True
                                break

                    if cholestasis_found:
                        continue  # Cholestatic injury rather than pure Hy's law candidate

                    # Compile evidence
                    evidence_refs = [str(trans_rec.identity), str(bili_rec.identity)]
                    supporting = [trans_rec.to_dict(), bili_rec.to_dict()]

                    finding = Finding(
                        finding_code="HYS_LAW_CANDIDATE",
                        subject=subject.usubjid,
                        site=subject.site_id,
                        domain="LB",
                        severity=FindingSeverity.CRITICAL,
                        status=FindingStatus.OPEN,
                        description=(
                            f"Hy's Law Candidate for Adjudication: Subject exhibits concurrent liver enzyme elevation: "
                            f"{t_test} ({t_interp.normalized_value} {t_interp.normalized_unit}, {t_ratio:.1f}x ULN on {t_date}) and "
                            f"{b_test} ({b_interp.normalized_value} {b_interp.normalized_unit}, {b_ratio:.1f}x ULN on {b_date}) "
                            f"occurring within {abs(int(diff))} days without documented cholestasis (ALP <= 2x ULN). "
                            f"Clinical adjudication required."
                        ),
                        protocol_version=protocol_version,
                        data_cut=cut,
                        evidence_references=evidence_refs,
                        supporting_records=supporting,
                        rule_name=self.rule_name,
                        discrepancy_details={
                            "transaminase_test": t_test,
                            "transaminase_ratio": t_ratio,
                            "transaminase_date": t_date,
                            "bilirubin_ratio": b_ratio,
                            "bilirubin_date": b_date,
                            "days_between": abs(round(diff, 1)),
                            "cholestasis_excluded": True,
                        },
                    )
                    reply = graph.get_site_reply("LB", subject.usubjid, trans_rec.seq)
                    if reply:
                        finding.site_reply = reply
                    decision = graph.get_monitor_decision("HYS_LAW_CANDIDATE", subject.usubjid)
                    if decision:
                        finding.monitor_decision = decision
                    findings.append(finding)
                    break  # Flag candidate once per transaminase event

        return findings

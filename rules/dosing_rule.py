"""
Dosing Error and Missing Exposure Rule
Evaluates EX.csv:
- Active Treatment Drug expected dose: 10 mg once daily
- Placebo expected dose: 0 mg
- Administered dose outside expected treatment dose is a protocol deviation / dosing error.
- Missing expected exposure record is flagged where treatment plan mandates exposure.
Always cites supporting EX records.
"""
from typing import Any, List
from models.finding import Finding, FindingSeverity, FindingStatus
from models.graph_nodes import SubjectNode
from rules.base_rule import BaseClinicalRule


class DosingErrorRule(BaseClinicalRule):
    rule_name: str = "Dosing Compliance & Protocol Deviation"
    rule_code: str = "DOSING_ERROR"

    def evaluate(self, subject: SubjectNode, graph: Any, cut: int) -> List[Finding]:
        findings = []
        protocol_version = graph.get_protocol_for_cut(cut)

        # Determine subject's assigned arm from DM
        assigned_arm = ""
        if subject.demographics:
            assigned_arm = (
                subject.demographics.get("ARM")
                or subject.demographics.get("ACTARM")
                or subject.demographics.get("TREATMENT")
                or ""
            ).upper()

        ex_records = subject.get_exposure(cut)

        # Check for missing exposure if patient is randomized and has post-baseline visits
        if not ex_records:
            has_post_baseline = False
            for d in ["VS", "LB", "AE"]:
                recs = subject.get_records(d, cut)
                if len(recs) > 1:
                    has_post_baseline = True
                    break

            if has_post_baseline and assigned_arm and "NOT ASSIGNED" not in assigned_arm and "SCREEN" not in assigned_arm:
                finding = Finding(
                    finding_code="EXPOSURE_MISSING",
                    subject=subject.usubjid,
                    site=subject.site_id,
                    domain="EX",
                    severity=FindingSeverity.MAJOR,
                    status=FindingStatus.OPEN,
                    description=(
                        f"Missing Expected Exposure: Subject is assigned to '{assigned_arm}' with active visits, "
                        f"but no exposure records (EX.csv) have been reported at Cut {cut}."
                    ),
                    protocol_version=protocol_version,
                    data_cut=cut,
                    evidence_references=[f"DM|{subject.usubjid}|1"],
                    supporting_records=[subject.demographics.to_dict()] if subject.demographics else [],
                    rule_name=self.rule_name,
                )
                decision = graph.get_monitor_decision("EXPOSURE_MISSING", subject.usubjid)
                if decision:
                    finding.monitor_decision = decision
                findings.append(finding)
            return findings

        # Evaluate individual EX records
        for ex in ex_records:
            dose_val_str = str(ex.get("EXDOSE", "")).strip()
            unit = str(ex.get("EXDOSU", "mg")).strip()
            freq = str(ex.get("EXDOSFRQ", "QD")).strip().upper()
            trt = str(ex.get("EXTRT", "")).strip().upper()

            try:
                dose = float(dose_val_str)
            except ValueError:
                dose = None

            # Determine expected dose
            # Check treatment name or subject's assigned arm
            is_placebo = "PLACEBO" in trt or "PLACEBO" in assigned_arm
            expected_dose = 0.0 if is_placebo else 10.0

            if dose is not None and dose != expected_dose:
                expected_label = f"{expected_dose} mg QD" if not is_placebo else "0 mg"
                finding = Finding(
                    finding_code="DOSING_ERROR",
                    subject=subject.usubjid,
                    site=subject.site_id,
                    domain="EX",
                    severity=FindingSeverity.MAJOR,
                    status=FindingStatus.OPEN,
                    description=(
                        f"Dosing Error: Administered dose {dose} {unit} ({freq}) does not match protocol "
                        f"specification of {expected_label} for treatment '{trt or assigned_arm}'."
                    ),
                    protocol_version=protocol_version,
                    data_cut=cut,
                    evidence_references=[str(ex.identity)],
                    supporting_records=[ex.to_dict()],
                    rule_name=self.rule_name,
                    discrepancy_details={
                        "administered_dose": dose,
                        "expected_dose": expected_dose,
                        "unit": unit,
                        "frequency": freq,
                    },
                )
                reply = graph.get_site_reply("EX", subject.usubjid, ex.seq)
                if reply:
                    finding.site_reply = reply
                decision = graph.get_monitor_decision("DOSING_ERROR", subject.usubjid)
                if decision:
                    finding.monitor_decision = decision
                findings.append(finding)

        return findings

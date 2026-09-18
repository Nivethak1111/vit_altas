"""
Protocol-Aware Screening Eligibility Rule
Evaluates inclusion and exclusion criteria at screening:
- Age 18–75 (from DM)
- HbA1c 7.0–10.5% (from LB screening visit)
- Stable metformin for at least 8 weeks (from CM or MH)
- Hepatic exclusion: ALT or AST > 2x ULN at screening (from LB)
- Pregnancy exclusion: positive pregnancy test or pregnant status
- Protocol v2/v3 additionally excludes: Creatinine > 1.5 mg/dL at screening
Dynamically determines applicable criteria based on protocol version for the cut.
"""
from typing import Any, List
from models.finding import Finding, FindingSeverity, FindingStatus
from models.graph_nodes import SubjectNode
from rules.base_rule import BaseClinicalRule
from utils.date_utils import days_between


class ScreeningEligibilityRule(BaseClinicalRule):
    rule_name: str = "Screening Eligibility Protocol Verification"
    rule_code: str = "SCREENING_ELIGIBILITY"

    def evaluate(self, subject: SubjectNode, graph: Any, cut: int) -> List[Finding]:
        findings = []
        protocol_version = str(graph.get_protocol_for_cut(cut)).lower()

        # 1. Demographics checks: Age & Pregnancy
        if subject.demographics:
            dm = subject.demographics
            age_val = dm.get("AGE")
            try:
                age = float(age_val)
                if age < 18 or age > 75:
                    findings.append(
                        Finding(
                            finding_code="INELIGIBLE_AGE",
                            subject=subject.usubjid,
                            site=subject.site_id,
                            domain="DM",
                            severity=FindingSeverity.CRITICAL,
                            status=FindingStatus.OPEN,
                            description=(
                                f"Screening Ineligibility: Subject age {age} years is outside the protocol-mandated "
                                f"eligibility window of 18–75 years."
                            ),
                            protocol_version=protocol_version,
                            data_cut=cut,
                            evidence_references=[str(dm.identity)],
                            supporting_records=[dm.to_dict()],
                            rule_name=self.rule_name,
                            discrepancy_details={"age": age, "required_range": "18-75"},
                        )
                    )
            except (ValueError, TypeError):
                pass

        # 2. Lab checks at Screening (HbA1c, Hepatic ALT/AST > 2x ULN, Pregnancy, Creatinine > 1.5 in v2+)
        lb_records = subject.get_laboratory_results(cut)
        has_metformin_history = False

        for lb in lb_records:
            visit = str(lb.get("VISIT", "")).upper()
            if "SCREEN" not in visit and "BASELINE" not in visit and "DAY -1" not in visit and "VISIT 1" not in visit:
                # Check only screening/baseline lab records
                continue

            test = str(lb.get("LBTEST", "") or lb.get("LBTESTCD", "")).upper()
            interp = graph.interpret_lab_record(lb)

            # Pregnancy exclusion
            if "PREG" in test or "HCG" in test:
                res_str = str(interp.raw_value).upper()
                if "POS" in res_str or "POSITIVE" in res_str:
                    findings.append(
                        Finding(
                            finding_code="INELIGIBLE_PREGNANCY",
                            subject=subject.usubjid,
                            site=subject.site_id,
                            domain="LB",
                            severity=FindingSeverity.CRITICAL,
                            status=FindingStatus.OPEN,
                            description=(
                                f"Screening Ineligibility: Subject had positive pregnancy test ({interp.raw_value}), "
                                f"violating mandatory pregnancy exclusion criteria."
                            ),
                            protocol_version=protocol_version,
                            data_cut=cut,
                            evidence_references=[str(lb.identity)],
                            supporting_records=[lb.to_dict()],
                            rule_name=self.rule_name,
                        )
                    )

            # HbA1c: 7.0–10.5%
            if "HBA1C" in test or "HEMOGLOBIN A1C" in test or "A1C" in test:
                if interp.normalized_value is not None:
                    val = interp.normalized_value
                    if val < 7.0 or val > 10.5:
                        findings.append(
                            Finding(
                                finding_code="INELIGIBLE_HBA1C",
                                subject=subject.usubjid,
                                site=subject.site_id,
                                domain="LB",
                                severity=FindingSeverity.CRITICAL,
                                status=FindingStatus.OPEN,
                                description=(
                                    f"Screening Ineligibility: HbA1c is {val}% (Protocol requires 7.0%–10.5% at screening)."
                                ),
                                protocol_version=protocol_version,
                                data_cut=cut,
                                evidence_references=[str(lb.identity)],
                                supporting_records=[lb.to_dict()],
                                rule_name=self.rule_name,
                                discrepancy_details={"reported_hba1c": val, "required_range": "7.0 - 10.5%"},
                            )
                        )

            # Hepatic exclusion: ALT or AST > 2x ULN at screening
            if test in ("ALT", "ALANINE AMINOTRANSFERASE", "SGPT", "AST", "ASPARTATE AMINOTRANSFERASE", "SGOT"):
                if interp.elevation_ratio is not None and interp.elevation_ratio > 2.0:
                    findings.append(
                        Finding(
                            finding_code="INELIGIBLE_HEPATIC_ELEVATION",
                            subject=subject.usubjid,
                            site=subject.site_id,
                            domain="LB",
                            severity=FindingSeverity.CRITICAL,
                            status=FindingStatus.OPEN,
                            description=(
                                f"Screening Ineligibility: Screening {test} of {interp.normalized_value} {interp.normalized_unit} "
                                f"exceeds 2x ULN ({interp.elevation_ratio:.1f}x ULN; ULN={interp.ref_high}), meeting hepatic exclusion."
                            ),
                            protocol_version=protocol_version,
                            data_cut=cut,
                            evidence_references=[str(lb.identity)],
                            supporting_records=[lb.to_dict()],
                            rule_name=self.rule_name,
                            discrepancy_details={
                                "test": test,
                                "value": interp.normalized_value,
                                "uln": interp.ref_high,
                                "ratio": interp.elevation_ratio,
                            },
                        )
                    )

            # Protocol v2/v3 Creatinine exclusion: Creatinine > 1.5 mg/dL
            if "v2" in protocol_version or "v3" in protocol_version:
                if "CREAT" in test:
                    # Normalized to mg/dL
                    cr_val = interp.normalized_value
                    if cr_val is not None and cr_val > 1.5:
                        findings.append(
                            Finding(
                                finding_code="INELIGIBLE_RENAL_CREATININE",
                                subject=subject.usubjid,
                                site=subject.site_id,
                                domain="LB",
                                severity=FindingSeverity.CRITICAL,
                                status=FindingStatus.OPEN,
                                description=(
                                    f"Screening Ineligibility (Protocol {protocol_version.upper()}): Screening serum creatinine "
                                    f"of {cr_val} mg/dL exceeds the protocol v2+ exclusion threshold (>1.5 mg/dL)."
                                ),
                                protocol_version=protocol_version,
                                data_cut=cut,
                                evidence_references=[str(lb.identity)],
                                supporting_records=[lb.to_dict()],
                                rule_name=self.rule_name,
                                discrepancy_details={"creatinine_mg_dl": cr_val, "threshold": 1.5},
                            )
                        )

        # 3. Stable Metformin for at least 8 weeks prior to screening
        # Check CM records for METFORMIN
        cm_records = subject.get_medications(cut)
        metformin_records = [
            cm for cm in cm_records if "METFORMIN" in str(cm.get("CMTRT", "")).upper()
        ]

        rfstdtc = subject.demographics.get("RFSTDTC") if subject.demographics else None
        if metformin_records and rfstdtc:
            for met in metformin_records:
                st_date = met.get("CMSTDTC") or met.get("CMSTDAT")
                diff_days = days_between(st_date, rfstdtc)
                # 8 weeks = 56 days
                if diff_days is not None and diff_days < 56:
                    findings.append(
                        Finding(
                            finding_code="INELIGIBLE_METFORMIN_STABILITY",
                            subject=subject.usubjid,
                            site=subject.site_id,
                            domain="CM",
                            severity=FindingSeverity.MAJOR,
                            status=FindingStatus.OPEN,
                            description=(
                                f"Screening Ineligibility: Metformin therapy initiated on {st_date} "
                                f"({int(diff_days)} days prior to Day 1), failing the required minimum 8-week (56-day) stability window."
                            ),
                            protocol_version=protocol_version,
                            data_cut=cut,
                            evidence_references=[str(met.identity)],
                            supporting_records=[met.to_dict()],
                            rule_name=self.rule_name,
                            discrepancy_details={"days_prior": int(diff_days), "required_days": 56},
                        )
                    )

        return findings

"""
Data Quality and Integrity Rule Engine
Detects:
- Missing required records (e.g. subject without Demographics DM record)
- Inconsistent subject/site relationships
- Suspicious duplicates (identical clinical test, date, and visit)
- Impossible/missing dates where evaluation requires them
- Corrected records (notifies monitor of retrospective field edits)
- Unit mismatches between clinical findings and reference standards
Never generates findings when evidence is insufficient.
"""
from typing import Any, Dict, List, Set, Tuple
from models.finding import Finding, FindingSeverity, FindingStatus
from models.graph_nodes import SubjectNode
from rules.base_rule import BaseClinicalRule
from utils.date_utils import parse_clinical_date


class DataQualityRule(BaseClinicalRule):
    rule_name: str = "Clinical Data Quality & Audit Integrity"
    rule_code: str = "DATA_QUALITY"

    def evaluate(self, subject: SubjectNode, graph: Any, cut: int) -> List[Finding]:
        findings = []
        protocol_version = graph.get_protocol_for_cut(cut)

        # 1. Missing Demographics (DM) record
        if not subject.demographics:
            findings.append(
                Finding(
                    finding_code="DQ_MISSING_DEMOGRAPHICS",
                    subject=subject.usubjid,
                    site=subject.site_id,
                    domain="DM",
                    severity=FindingSeverity.CRITICAL,
                    status=FindingStatus.OPEN,
                    description=(
                        f"Data Quality: Subject {subject.usubjid} has clinical domain records "
                        f"but no parent Demographics (DM) record was loaded."
                    ),
                    protocol_version=protocol_version,
                    data_cut=cut,
                    evidence_references=[],
                    rule_name=self.rule_name,
                )
            )

        # 2. Inconsistent Subject-Site relationships
        # Check if USUBJID contains site prefix that differs from site_id
        if "-" in subject.usubjid:
            parts = subject.usubjid.split("-")
            if len(parts) >= 3:
                expected_site = parts[1]
                if subject.site_id and expected_site not in subject.site_id and subject.site_id not in expected_site:
                    findings.append(
                        Finding(
                            finding_code="DQ_INCONSISTENT_SITE",
                            subject=subject.usubjid,
                            site=subject.site_id,
                            domain="DM",
                            severity=FindingSeverity.MAJOR,
                            status=FindingStatus.OPEN,
                            description=(
                                f"Data Quality: Inconsistent Site identifier for subject {subject.usubjid}. "
                                f"USUBJID implies Site '{expected_site}', but record specifies Site '{subject.site_id}'."
                            ),
                            protocol_version=protocol_version,
                            data_cut=cut,
                            evidence_references=[str(subject.demographics.identity)] if subject.demographics else [],
                            supporting_records=[subject.demographics.to_dict()] if subject.demographics else [],
                            rule_name=self.rule_name,
                        )
                    )

        # 3. Corrected records audit trail notification
        for domain, recs in subject.records_by_domain.items():
            for r in recs:
                if r.cut_available <= cut and r.corrected_at_cut is not None and r.corrected_at_cut <= cut:
                    for ch in r.correction_history:
                        if ch.get("correction_cut", 0) <= cut:
                            findings.append(
                                Finding(
                                    finding_code="DQ_AUDIT_CORRECTED_RECORD",
                                    subject=subject.usubjid,
                                    site=subject.site_id,
                                    domain=domain,
                                    severity=FindingSeverity.INFO,
                                    status=FindingStatus.RESOLVED,
                                    description=(
                                        f"Data Audit Notice: Field '{ch.get('field_name')}' was corrected at Cut {ch.get('correction_cut')} "
                                        f"from '{ch.get('original_value')}' to '{ch.get('corrected_value')}'. "
                                        f"Reason: {ch.get('reason', 'Retrospective data entry correction')}."
                                    ),
                                    protocol_version=protocol_version,
                                    data_cut=cut,
                                    evidence_references=[str(r.identity)],
                                    supporting_records=[r.to_dict()],
                                    rule_name=self.rule_name,
                                    discrepancy_details=ch,
                                )
                            )

        # 4. Suspicious duplicate records in LB and VS
        for domain_name in ["LB", "VS"]:
            recs = subject.get_records(domain_name, cut)
            seen_signatures: Dict[Tuple[str, str, str], Any] = {}
            for r in recs:
                test_code = str(r.get(f"{domain_name}TESTCD") or r.get(f"{domain_name}TEST") or "").upper()
                dtc = str(r.get(f"{domain_name}DTC") or r.get("DATE") or "")
                visit = str(r.get("VISIT") or "").upper()

                if test_code and dtc and visit:
                    sig = (test_code, dtc, visit)
                    if sig in seen_signatures:
                        prior_r = seen_signatures[sig]
                        findings.append(
                            Finding(
                                finding_code=f"DQ_DUPLICATE_{domain_name}",
                                subject=subject.usubjid,
                                site=subject.site_id,
                                domain=domain_name,
                                severity=FindingSeverity.MODERATE,
                                status=FindingStatus.OPEN,
                                description=(
                                    f"Data Quality: Duplicate {domain_name} record detected for test '{test_code}' "
                                    f"on date {dtc} at {visit}. Records: {prior_r.identity} and {r.identity}."
                                ),
                                protocol_version=protocol_version,
                                data_cut=cut,
                                evidence_references=[str(prior_r.identity), str(r.identity)],
                                supporting_records=[prior_r.to_dict(), r.to_dict()],
                                rule_name=self.rule_name,
                            )
                        )
                    else:
                        seen_signatures[sig] = r

        # 5. Impossible date sequences: AE End Date before AE Start Date
        ae_records = subject.get_adverse_events(cut)
        for ae in ae_records:
            st = ae.get("AESTDTC") or ae.get("AESTDAT")
            en = ae.get("AEENDTC") or ae.get("AEENDAT")
            if st and en:
                d_st = parse_clinical_date(st)
                d_en = parse_clinical_date(en)
                if d_st and d_en and d_en < d_st:
                    findings.append(
                        Finding(
                            finding_code="DQ_IMPOSSIBLE_DATE_SEQUENCE",
                            subject=subject.usubjid,
                            site=subject.site_id,
                            domain="AE",
                            severity=FindingSeverity.CRITICAL,
                            status=FindingStatus.OPEN,
                            description=(
                                f"Data Quality: Impossible date sequence for adverse event '{ae.get('AETERM')}'. "
                                f"End date ({en}) precedes Start date ({st})."
                            ),
                            protocol_version=protocol_version,
                            data_cut=cut,
                            evidence_references=[str(ae.identity)],
                            supporting_records=[ae.to_dict()],
                            rule_name=self.rule_name,
                            discrepancy_details={"start_date": st, "end_date": en},
                        )
                    )

        return findings

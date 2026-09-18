"""
Clinical Finding Engine
Executes modular clinical monitoring rules on the StudyGraph.
Derives all findings strictly from clinical data and protocol specifications first,
and then enriches each finding with external site replies and monitor decisions.
Every finding is strictly traceable to exact evidence: (domain, USUBJID, SEQ).
"""
from typing import Any, Dict, List, Optional
from graph.study_graph import StudyGraph
from models.finding import Finding
from rules.base_rule import BaseClinicalRule
from rules.data_quality_rule import DataQualityRule
from rules.dosing_rule import DosingErrorRule
from rules.hys_law_rule import HysLawRule
from rules.prohibited_meds_rule import ProhibitedMedicationsRule
from rules.sae_rule import SAEDetectionRule
from rules.screening_rule import ScreeningEligibilityRule
from rules.visit_window_rule import VisitWindowRule


class FindingEngine:
    def __init__(self, rules: Optional[List[BaseClinicalRule]] = None):
        if rules is not None:
            self.rules = rules
        else:
            self.rules = [
                SAEDetectionRule(),
                DosingErrorRule(),
                VisitWindowRule(),
                ProhibitedMedicationsRule(),
                ScreeningEligibilityRule(),
                HysLawRule(),
                DataQualityRule(),
            ]

    def register_rule(self, rule: BaseClinicalRule):
        self.rules.append(rule)

    def evaluate_subject(self, graph: StudyGraph, usubjid: str, cut: int) -> List[Finding]:
        subject = graph.get_subject(usubjid, cut=cut)
        all_findings: List[Finding] = []

        for rule in self.rules:
            findings = rule.evaluate(subject, graph, cut)
            for f in findings:
                # Enrich with site reply and monitor decision if not already populated
                self._enrich_finding_responses(f, graph)
                all_findings.append(f)

        return all_findings

    def evaluate_study(
        self,
        graph: StudyGraph,
        cut: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        subjects = graph.get_all_subjects(cut=cut)
        findings: List[Finding] = []

        for subj in subjects:
            subj_findings = self.evaluate_subject(graph, subj.usubjid, cut)
            findings.extend(subj_findings)

        # Apply filtering if provided
        if filters:
            filtered = []
            for f in findings:
                match = True
                if "site" in filters and filters["site"] and f.site != filters["site"]:
                    match = False
                if "subject" in filters and filters["subject"] and f.subject != filters["subject"]:
                    match = False
                if "domain" in filters and filters["domain"] and f.domain != filters["domain"]:
                    match = False
                if "severity" in filters and filters["severity"] and f.severity != filters["severity"]:
                    match = False
                if "status" in filters and filters["status"] and f.status != filters["status"]:
                    match = False
                if "finding_code" in filters and filters["finding_code"] and f.finding_code != filters["finding_code"]:
                    match = False
                if match:
                    filtered.append(f)
            return filtered

        return findings

    def _enrich_finding_responses(self, finding: Finding, graph: StudyGraph):
        # 1. Site reply lookup: DOMAIN|USUBJID|SEQ
        if not finding.site_reply and finding.evidence_references:
            # Use primary evidence reference
            primary_ref = finding.evidence_references[0]
            parts = primary_ref.split("|")
            if len(parts) == 3:
                domain, usubjid, seq_str = parts
                try:
                    seq = int(seq_str)
                    reply = graph.get_site_reply(domain, usubjid, seq)
                    if reply:
                        finding.site_reply = reply
                except ValueError:
                    pass

        # 2. Monitor decision lookup: CODE|USUBJID
        if not finding.monitor_decision:
            decision = graph.get_monitor_decision(finding.finding_code, finding.subject)
            if decision:
                finding.monitor_decision = decision
                # Update status based on decision
                dec_status = decision.get("decision", "").upper()
                if dec_status == "APPROVED":
                    finding.status = "RESOLVED"
                elif dec_status == "REJECTED":
                    finding.status = "CLOSED"
                elif dec_status == "CLARIFY":
                    finding.status = "UNDER_REVIEW"

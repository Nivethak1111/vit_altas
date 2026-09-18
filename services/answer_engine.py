"""
Answer Engine Service
Implements the clinical monitoring decision & question answering flow:
USER QUESTION
   -> Query Understanding
   -> Question Type
   -> [StudyGraph | Rule Engine]
   -> Evidence
   -> Site/Monitor Data
   -> Synthesized Clinical Answer
"""
from typing import Any, Dict, List, Optional
from graph.graph_statistics import GraphStatistics
from graph.study_graph import StudyGraph
from models.query import AnswerResponse, ExtractedEntities, QuestionType
from services.finding_engine import FindingEngine
from services.query_understanding import QueryUnderstandingService


class AnswerEngine:
    def __init__(self, graph: StudyGraph, finding_engine: Optional[FindingEngine] = None):
        self.graph = graph
        self.finding_engine = finding_engine or FindingEngine()

    def answer(self, question: str, cut: Optional[int] = None) -> AnswerResponse:
        active_cuts = self.graph.cut_manager.get_available_cuts()
        resolved_cut = cut if cut is not None else (active_cuts[-1] if active_cuts else 1)
        available_subjects = list(self.graph._subjects.keys())

        # Step 1 & 2: Query Understanding & Entity Extraction
        entities = QueryUnderstandingService.parse_query(
            question, default_cut=resolved_cut, available_subjects=available_subjects
        )
        eval_cut = entities.cut or resolved_cut
        protocol_version = self.graph.get_protocol_for_cut(eval_cut)

        # Step 3: Question Type Classification
        q_type = QueryUnderstandingService.classify_question_type(question, entities)

        evidence_references: List[str] = []
        supporting_records: List[Dict[str, Any]] = []
        findings_data: List[Dict[str, Any]] = []
        site_replies: List[Dict[str, Any]] = []
        monitor_decisions: List[Dict[str, Any]] = []
        direct_answer = ""
        clinical_rationale = ""

        # Step 4: Branching Execution [StudyGraph | Rule Engine]
        if q_type == QuestionType.STUDY_STATISTICS:
            stats = GraphStatistics.calculate(self.graph, cut=eval_cut)
            direct_answer = (
                f"Study {self.graph.study_id} at Cut {eval_cut} (active Protocol {protocol_version.upper()}) "
                f"contains {stats['subject_count']} enrolled subjects across {stats['site_count']} investigational sites, "
                f"with {stats['total_records']} clinical records available. "
                f"Domain breakdown: {', '.join([f'{d}: {c}' for d, c in stats['domain_record_counts'].items()])}. "
                f"Total applied corrections: {stats['correction_count']}."
            )
            clinical_rationale = "Generated from dynamic StudyGraph statistics engine."

        elif q_type == QuestionType.RULE_EVALUATION:
            # Route to Rule Engine
            if entities.subject_id:
                findings = self.finding_engine.evaluate_subject(self.graph, entities.subject_id, cut=eval_cut)
            else:
                findings = self.finding_engine.evaluate_study(
                    self.graph, cut=eval_cut, filters={"site": entities.site_id, "domain": entities.domain}
                )

            # Filter findings by clinical concept if specified
            if entities.clinical_concept:
                concept = entities.clinical_concept.upper()
                matched_f = [
                    f for f in findings
                    if concept in f.finding_code or concept in f.description.upper() or concept in f.domain
                ]
                if matched_f:
                    findings = matched_f

            findings_data = [f.to_dict() for f in findings]

            if not findings:
                direct_answer = (
                    f"No protocol violations, safety signals, or data quality deviations were detected "
                    f"under active Protocol {protocol_version.upper()} at Cut {eval_cut}"
                    + (f" for subject {entities.subject_id}." if entities.subject_id else ".")
                )
                clinical_rationale = "Evaluated across all active clinical monitoring rules."
            else:
                top_findings_desc = "; ".join([f"{f.finding_code}: {f.description}" for f in findings[:3]])
                direct_answer = (
                    f"Identified {len(findings)} clinical finding(s) under Protocol {protocol_version.upper()} at Cut {eval_cut}: "
                    f"{top_findings_desc}."
                )
                clinical_rationale = f"Derived by Finding Engine applying Protocol {protocol_version.upper()} criteria."

                # Step 5: Gather Evidence from Findings
                for f in findings:
                    for ev in f.evidence_references:
                        if ev not in evidence_references:
                            evidence_references.append(ev)
                    supporting_records.extend(f.supporting_records)
                    if f.site_reply and f.site_reply not in site_replies:
                        site_replies.append(f.site_reply)
                    if f.monitor_decision and f.monitor_decision not in monitor_decisions:
                        monitor_decisions.append(f.monitor_decision)

        elif q_type == QuestionType.HYBRID_MONITORING:
            # Route to BOTH StudyGraph and Rule Engine
            target_subjid = entities.subject_id
            if target_subjid and target_subjid in self.graph._subjects:
                subject_node = self.graph.get_subject(target_subjid, cut=eval_cut)
                findings = self.finding_engine.evaluate_subject(self.graph, target_subjid, cut=eval_cut)
                findings_data = [f.to_dict() for f in findings]

                # StudyGraph Domain Traversal
                dom = entities.domain or "AE"
                records = subject_node.get_records(dom, cut=eval_cut)
                supporting_records = [r.to_dict() for r in records]
                evidence_references = [str(r.identity) for r in records]

                # Step 6: Site/Monitor Data
                for r in records:
                    reply = self.graph.get_site_reply(r.domain, target_subjid, r.seq)
                    if reply and reply not in site_replies:
                        site_replies.append(reply)

                for f in findings:
                    if f.monitor_decision and f.monitor_decision not in monitor_decisions:
                        monitor_decisions.append(f.monitor_decision)

                if findings:
                    finding_summaries = " | ".join([f"{f.finding_code}: {f.description}" for f in findings])
                    direct_answer = (
                        f"Subject {target_subjid} (Site {subject_node.site_id}) has {len(records)} {dom} record(s) "
                        f"and {len(findings)} active clinical finding(s) at Cut {eval_cut} (Protocol {protocol_version.upper()}): {finding_summaries}."
                    )
                else:
                    direct_answer = (
                        f"Subject {target_subjid} (Site {subject_node.site_id}) has {len(records)} {dom} record(s) "
                        f"with no active protocol deviations at Cut {eval_cut}."
                    )
                clinical_rationale = "Synthesized from StudyGraph domain records, rule-based safety evaluation, and external monitoring responses."

            else:
                # General hybrid query without specific subject
                findings = self.finding_engine.evaluate_study(self.graph, cut=eval_cut)
                findings_data = [f.to_dict() for f in findings]
                direct_answer = (
                    f"At Cut {eval_cut} (Protocol {protocol_version.upper()}), {len(findings)} total findings are active across the study."
                )
                for f in findings:
                    evidence_references.extend(f.evidence_references)
                    supporting_records.extend(f.supporting_records)
                    if f.site_reply:
                        site_replies.append(f.site_reply)
                    if f.monitor_decision:
                        monitor_decisions.append(f.monitor_decision)
                clinical_rationale = "Generated across all study subjects and monitoring responses."

        else:
            # FACTUAL_RETRIEVAL -> StudyGraph Traversal
            target_subjid = entities.subject_id
            if target_subjid and target_subjid in self.graph._subjects:
                subj = self.graph.get_subject(target_subjid, cut=eval_cut)
                dom = entities.domain or "DM"
                recs = subj.get_records(dom, cut=eval_cut)
                supporting_records = [r.to_dict() for r in recs]
                evidence_references = [str(r.identity) for r in recs]

                # Format factual answer
                if dom == "DM" and subj.demographics:
                    d = subj.demographics
                    direct_answer = (
                        f"Subject {target_subjid} is enrolled at Site {subj.site_id}, randomized to ARM '{d.get('ARM')}', "
                        f"Age {d.get('AGE')} ({d.get('SEX')}), with Day 1 start date {d.get('RFSTDTC')}."
                    )
                elif dom == "EX":
                    ex_details = [f"{r.get('EXTRT')} {r.get('EXDOSE')} {r.get('EXDOSU')} ({r.get('EXDOSFRQ')})" for r in recs]
                    direct_answer = (
                        f"Subject {target_subjid} has {len(recs)} exposure record(s) at Cut {eval_cut}: {', '.join(ex_details)}."
                    )
                elif dom == "AE":
                    ae_details = [f"'{r.get('AETERM')}' (Serious: {r.get('AESER')}, Hosp: {r.get('AESHOSP')})" for r in recs]
                    direct_answer = (
                        f"Subject {target_subjid} experienced {len(recs)} adverse event(s) at Cut {eval_cut}: {', '.join(ae_details)}."
                    )
                elif dom == "LB":
                    lb_details = [f"{r.get('LBTEST') or r.get('LBTESTCD')}: {r.get('LBORRES')} {r.get('LBORRESU')}" for r in recs[:5]]
                    direct_answer = (
                        f"Subject {target_subjid} has {len(recs)} laboratory record(s) at Cut {eval_cut}. Sample results: {'; '.join(lb_details)}."
                    )
                else:
                    direct_answer = (
                        f"Subject {target_subjid} has {len(recs)} {dom} record(s) available at Cut {eval_cut}."
                    )
                clinical_rationale = f"Retrieved directly from StudyGraph {dom} domain records."

                # External responses
                for r in recs:
                    reply = self.graph.get_site_reply(r.domain, target_subjid, r.seq)
                    if reply and reply not in site_replies:
                        site_replies.append(reply)

            else:
                # Factual query across all subjects for a domain
                dom = entities.domain or "AE"
                recs = self.graph.get_records(dom, cut=eval_cut)
                supporting_records = [r.to_dict() for r in recs[:10]]
                evidence_references = [str(r.identity) for r in recs[:10]]
                direct_answer = (
                    f"A total of {len(recs)} {dom} records are available in the study at Cut {eval_cut}."
                )
                clinical_rationale = f"Traversed StudyGraph for all {dom} domain records."

        # Handle TRAP / NO-FINDING
        if q_type != QuestionType.STUDY_STATISTICS and not findings_data and not supporting_records and not evidence_references:
            direct_answer = "None found."

        # Count mapping
        count_val = None
        q_lower = question.lower()
        is_count_q = any(w in q_lower for w in ["count", "how many"])

        if q_type == QuestionType.STUDY_STATISTICS:
            if entities.domain:
                count_val = stats['domain_record_counts'].get(entities.domain, 0)
            else:
                count_val = stats['total_records']
        elif is_count_q:
            if "subject" in q_lower or "subjects" in q_lower:
                if findings_data:
                    subjects_with_findings = set(f.get('subject_id') for f in findings_data if f.get('subject_id'))
                    count_val = len(subjects_with_findings)
                    direct_answer = f"{count_val} subject(s) match the criteria."
                elif supporting_records:
                    subjects_with_recs = set(r.get('USUBJID') for r in supporting_records if r.get('USUBJID'))
                    count_val = len(subjects_with_recs)
                    direct_answer = f"{count_val} subject(s) match the criteria."
                else:
                    count_val = 0
            else:
                if findings_data:
                    count_val = len(findings_data)
                    direct_answer = f"Found {count_val} matching finding(s)."
                elif supporting_records:
                    count_val = len(supporting_records)
                    direct_answer = f"Found {count_val} matching record(s)."
                else:
                    count_val = 0

        return AnswerResponse(
            question=question,
            question_type=q_type,
            entities=entities,
            answer=direct_answer,
            protocol_version=protocol_version,
            cut=eval_cut,
            count=count_val,
            evidence=evidence_references,
            supporting_records=supporting_records,
            findings=findings_data,
            site_reply=site_replies,
            monitor_decision=monitor_decisions,
            explanation=clinical_rationale,
        )

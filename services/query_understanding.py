"""
Query Understanding & Intent Classification Service
Parses natural language clinical questions, extracts entities (Subject, Site, Domain, Cut, Concept),
and classifies the Question Type:
- FACTUAL_RETRIEVAL -> StudyGraph
- RULE_EVALUATION   -> Rule Engine
- HYBRID_MONITORING -> StudyGraph + Rule Engine
- STUDY_STATISTICS  -> Dynamic Statistics Engine
"""
import re
from typing import Any, List, Optional
from models.query import ExtractedEntities, QuestionType


class QueryUnderstandingService:
    KNOWN_DOMAINS = ["DM", "AE", "LB", "VS", "EX", "CM", "DS", "MH", "EG"]

    RULE_KEYWORDS = [
        "sae", "serious", "discrepancy", "hospitalization", "delay", "reporting",
        "dosing error", "dose deviation", "overdose", "missing exposure",
        "prohibited", "glucocorticoid", "prednisone", "sulfonylurea", "glimepiride",
        "hy's law", "hys law", "hepatotoxicity", "liver injury",
        "screening", "eligibility", "ineligible", "inclusion", "exclusion",
        "visit window", "out of window", "window deviation",
        "data quality", "duplicate", "impossible date", "flagged", "violation"
    ]

    RESPONSE_KEYWORDS = [
        "reply", "replies", "query", "queries", "monitor", "decision", "clarify",
        "approved", "rejected", "adjudication", "investigator", "cra"
    ]

    STATISTICS_KEYWORDS = [
        "how many", "count", "total subjects", "total sites", "total records",
        "statistics", "breakdown", "progression", "overall"
    ]

    @classmethod
    def parse_query(cls, question: str, default_cut: int = 1, available_subjects: Optional[List[str]] = None) -> ExtractedEntities:
        q_lower = question.lower()

        entities = ExtractedEntities(cut=default_cut)

        # 1. Cut extraction (e.g., "cut 1", "cut 2", "cut 3", "in cut 2")
        cut_match = re.search(r"\bcut\s*(\d+)\b", q_lower)
        if cut_match:
            entities.cut = int(cut_match.group(1))

        # 2. Subject ID extraction
        # Look for full USUBJID (e.g. STUDY042-101-001) or short pattern (101-001 or 001)
        subj_match = re.search(r"\b([a-zA-Z0-9]+-[0-9]{3}-[0-9]{3})\b", question)
        if subj_match:
            entities.subject_id = subj_match.group(1)
        elif available_subjects:
            # Check if partial subject matches
            for subj in available_subjects:
                if subj.lower() in q_lower:
                    entities.subject_id = subj
                    break
                # Check last part (e.g. 101-002)
                parts = subj.split("-")
                if len(parts) >= 3 and f"{parts[1]}-{parts[2]}".lower() in q_lower:
                    entities.subject_id = subj
                    break

        # 3. Site ID extraction
        site_match = re.search(r"\b(site-?\s*([0-9]{2,3}))\b", q_lower)
        if site_match:
            site_num = site_match.group(2)
            entities.site_id = f"SITE-{site_num}"

        # 4. Domain extraction
        for d in cls.KNOWN_DOMAINS:
            # Match whole word domain
            if re.search(rf"\b{d.lower()}\b", q_lower):
                entities.domain = d
                break

        # Map common terms to domains if not explicitly named
        if not entities.domain:
            if any(w in q_lower for w in ["adverse", "event", "ae", "safety", "toxic", "hosp"]):
                entities.domain = "AE"
            elif any(w in q_lower for w in ["lab", "test", "alt", "ast", "bilirubin", "creatinine", "hba1c"]):
                entities.domain = "LB"
            elif any(w in q_lower for w in ["dose", "dosing", "exposure", "drug", "placebo"]):
                entities.domain = "EX"
            elif any(w in q_lower for w in ["medication", "conmed", "steroid", "prednisone", "sulfonylurea"]):
                entities.domain = "CM"
            elif any(w in q_lower for w in ["vital", "blood pressure", "pulse", "systolic", "diastolic"]):
                entities.domain = "VS"
            elif any(w in q_lower for w in ["demographic", "age", "sex", "race", "baseline"]):
                entities.domain = "DM"

        # 5. Clinical concept extraction
        for kw in cls.RULE_KEYWORDS:
            if kw in q_lower:
                entities.clinical_concept = kw.upper().replace(" ", "_")
                break

        return entities

    @classmethod
    def classify_question_type(cls, question: str, entities: ExtractedEntities) -> str:
        q_lower = question.lower()

        has_rule_kw = any(w in q_lower for w in cls.RULE_KEYWORDS)
        has_resp_kw = any(w in q_lower for w in cls.RESPONSE_KEYWORDS)

        # Check for count statistics specifically without rules
        if any(w in q_lower for w in cls.STATISTICS_KEYWORDS) and not entities.subject_id and not has_rule_kw:
            return QuestionType.STUDY_STATISTICS

        if has_rule_kw and (has_resp_kw or "why" in q_lower or entities.subject_id):
            return QuestionType.HYBRID_MONITORING

        if has_rule_kw:
            return QuestionType.RULE_EVALUATION

        # Otherwise factual retrieval from StudyGraph
        return QuestionType.FACTUAL_RETRIEVAL

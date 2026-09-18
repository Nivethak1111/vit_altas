"""
Query and Answer Engine Data Models
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class QuestionType:
    FACTUAL_RETRIEVAL = "FACTUAL_RETRIEVAL"     # Direct queries into StudyGraph
    RULE_EVALUATION = "RULE_EVALUATION"         # Clinical safety & protocol checks via Rule Engine
    HYBRID_MONITORING = "HYBRID_MONITORING"     # Both StudyGraph retrieval and Rule findings
    STUDY_STATISTICS = "STUDY_STATISTICS"       # Aggregate statistics across study/cuts


@dataclass
class ExtractedEntities:
    subject_id: Optional[str] = None
    site_id: Optional[str] = None
    domain: Optional[str] = None
    cut: Optional[int] = None
    clinical_concept: Optional[str] = None
    test_name: Optional[str] = None
    medication_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "site_id": self.site_id,
            "domain": self.domain,
            "cut": self.cut,
            "clinical_concept": self.clinical_concept,
            "test_name": self.test_name,
            "medication_name": self.medication_name,
        }


@dataclass
class AnswerResponse:
    question: str
    question_type: str
    entities: ExtractedEntities
    answer: str
    protocol_version: str
    cut: int
    count: Optional[int] = None
    evidence: List[str] = field(default_factory=list)  # ["DOMAIN|USUBJID|SEQ"]
    supporting_records: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    site_reply: List[Dict[str, Any]] = field(default_factory=list)
    monitor_decision: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "question_type": self.question_type,
            "entities": self.entities.to_dict(),
            "answer": self.answer,
            "protocol_version": self.protocol_version,
            "cut": self.cut,
            "count": self.count,
            "evidence": self.evidence,
            "supporting_records": self.supporting_records,
            "findings": self.findings,
            "site_reply": self.site_reply,
            "monitor_decision": self.monitor_decision,
            "explanation": self.explanation,
        }

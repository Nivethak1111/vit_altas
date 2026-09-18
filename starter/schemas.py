from dataclasses import dataclass, field
from typing import List, Any, Optional

@dataclass
class RecordRef:
    domain: str
    usubjid: str
    seq: int
    document: str
    section: str

@dataclass
class Question:
    id: str
    text: str

@dataclass
class Answer:
    question_id: str
    answer: Any
    text: str
    evidence: List[RecordRef]
    confidence: float
    steps_used: int
    tokens_used: int

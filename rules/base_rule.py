"""
Base Rule Interface for ATLAS Clinical Monitoring Finding Engine
"""
from abc import ABC, abstractmethod
from typing import Any, List
from models.finding import Finding
from models.graph_nodes import SubjectNode


class BaseClinicalRule(ABC):
    rule_name: str = "BASE_RULE"
    rule_code: str = "BASE"

    @abstractmethod
    def evaluate(self, subject: SubjectNode, graph: Any, cut: int) -> List[Finding]:
        """Evaluates clinical rule against a subject at a specific data cut."""
        pass

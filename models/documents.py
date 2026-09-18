"""
Study Document Models (Reference Evidence only - never executed)
"""
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class StudyDocument:
    name: str
    doc_type: str  # protocol, lab_manual, sap, etc.
    version: str
    content: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "doc_type": self.doc_type,
            "version": self.version,
            "content": self.content,
            "size_chars": len(self.content),
        }

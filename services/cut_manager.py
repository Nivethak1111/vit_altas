"""
Cut Manager Service
Manages data cuts, cut filtering (cut_available <= N),
and dynamically maps active protocol versions from cuts.csv metadata.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CutMetadata:
    cut_id: int
    cut_date: str
    protocol_version: str  # e.g. "v1", "v2", "v3" or "Protocol v1"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cut_id": self.cut_id,
            "cut_date": self.cut_date,
            "protocol_version": self.protocol_version,
            "description": self.description,
        }


class CutManager:
    def __init__(self, cuts: Optional[List[CutMetadata]] = None):
        self._cuts: Dict[int, CutMetadata] = {}
        if cuts:
            for c in cuts:
                self.add_cut(c)

    def add_cut(self, cut: CutMetadata):
        self._cuts[cut.cut_id] = cut

    def get_cut(self, cut_id: int) -> Optional[CutMetadata]:
        return self._cuts.get(cut_id)

    def get_available_cuts(self) -> List[int]:
        return sorted(self._cuts.keys())

    def get_all_cuts(self) -> List[CutMetadata]:
        return [self._cuts[k] for k in sorted(self._cuts.keys())]

    def get_protocol_for_cut(self, cut_id: int) -> str:
        cut_meta = self.get_cut(cut_id)
        if cut_meta:
            return cut_meta.protocol_version
        # If cuts metadata was not explicitly loaded or empty, fallback cleanly
        return "v1"

    def is_cut_valid(self, cut_id: int) -> bool:
        return cut_id in self._cuts

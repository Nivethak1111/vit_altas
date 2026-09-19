from typing import Any
import sys
import os

# Ensure the parent directory is in sys.path so we can import vit_altas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graph.study_graph import StudyGraph as InternalStudyGraph
from services.answer_engine import AnswerEngine
from starter.schemas import Question, Answer, RecordRef

class StudyGraph:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self._internal_graph = InternalStudyGraph.load_study(self.data_dir)
        self.active_cut = None
        
    def build(self, cut: int = None):
        """Builds or rebuilds the graph up to the specified cut."""
        import time
        start = time.time()
        self.active_cut = cut
        
        from graph.graph_statistics import GraphStatistics
        stats = GraphStatistics.calculate(self._internal_graph, cut=cut)
        build_ms = int((time.time() - start) * 1000)
        
        return {
            "nodes": stats.get("subject_count", 0) + stats.get("total_records", 0) + stats.get("site_count", 0),
            "edges": stats.get("total_records", 0),
            "subjects": stats.get("subject_count", 0),
            "build_ms": build_ms,
            "cut": cut
        }
        
    def patient360(self, usubjid: str) -> dict:
        # Get patient data dynamically filtered by active_cut if needed
        from services.patient360_service import Patient360Service
        from services.finding_engine import FindingEngine
        p360 = Patient360Service(FindingEngine())
        return p360.get_patient_profile(self._internal_graph, usubjid, self.active_cut)


class Atlas:
    def __init__(self, graph: StudyGraph):
        self.graph = graph
        self.engine = AnswerEngine(graph._internal_graph)
        
    def answer(self, question: Question) -> Answer:
        # Get internal response
        response = self.engine.answer(question.text, cut=self.graph.active_cut)
        
        # Convert internal evidence (e.g. "LB|SUBJ-001|2") to RecordRef
        record_refs = []
        for ev in response.evidence:
            parts = ev.split('|')
            if len(parts) >= 3:
                domain, usubjid, seq = parts[0], parts[1], parts[2]
                try:
                    seq_int = int(seq)
                except ValueError:
                    seq_int = 0
                record_refs.append(RecordRef(
                    domain=domain,
                    usubjid=usubjid,
                    seq=seq_int,
                    document="",
                    section=""
                ))
            
        # Count handling
        if response.count is not None:
            ans_val = response.count
        else:
            ans_val = response.answer
            # Trap handling (return [] if none found)
            if ans_val == "None found." or ans_val == "None found":
                ans_val = []
            
        # Wrap into official Answer schema
        return Answer(
            question_id=question.id,
            answer=ans_val,
            text=response.explanation,
            evidence=record_refs,
            confidence=1.0, # Placeholder
            steps_used=1, # Placeholder
            tokens_used=100 # Placeholder
        )

"""
Automated Tests for the Answer Engine Pipeline
Validates the flow:
USER QUESTION -> Query Understanding -> Question Type -> [StudyGraph | Rule Engine] -> Evidence -> Site/Monitor -> Answer
"""
import os
import sys
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from graph.study_graph import StudyGraph
from models.query import QuestionType
from services.answer_engine import AnswerEngine
from services.finding_engine import FindingEngine
from services.query_understanding import QueryUnderstandingService


class TestAnswerEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study_dir = os.path.join(ROOT_DIR, "data", "STUDY-042")
        cls.graph = StudyGraph.load_study(cls.study_dir)
        cls.finding_engine = FindingEngine()
        cls.engine = AnswerEngine(cls.graph, cls.finding_engine)

    def test_01_query_understanding_entity_extraction(self):
        """Verifies subject, domain, cut, and concept extraction."""
        q = "What adverse events occurred for subject STUDY042-101-002 at Cut 1?"
        entities = QueryUnderstandingService.parse_query(q)
        self.assertEqual(entities.subject_id, "STUDY042-101-002")
        self.assertEqual(entities.domain, "AE")
        self.assertEqual(entities.cut, 1)

    def test_02_question_type_classification(self):
        """Verifies classification of question types."""
        # Factual query
        q_fact = "What dose of study drug was given to subject STUDY042-101-001?"
        ent_fact = QueryUnderstandingService.parse_query(q_fact)
        type_fact = QueryUnderstandingService.classify_question_type(q_fact, ent_fact)
        self.assertEqual(type_fact, QuestionType.FACTUAL_RETRIEVAL)

        # Rule evaluation query
        q_rule = "Are there any dosing errors in the study at Cut 1?"
        ent_rule = QueryUnderstandingService.parse_query(q_rule)
        type_rule = QueryUnderstandingService.classify_question_type(q_rule, ent_rule)
        self.assertEqual(type_rule, QuestionType.RULE_EVALUATION)

        # Hybrid query (subject + rule/discrepancy)
        q_hyb = "Why was subject STUDY042-101-002 flagged for an SAE discrepancy and what was the site reply?"
        ent_hyb = QueryUnderstandingService.parse_query(q_hyb)
        type_hyb = QueryUnderstandingService.classify_question_type(q_hyb, ent_hyb)
        self.assertEqual(type_hyb, QuestionType.HYBRID_MONITORING)

    def test_03_factual_answer_via_study_graph(self):
        """Verifies StudyGraph retrieval and evidence citations."""
        res = self.engine.answer("What is the demographic profile for subject STUDY042-101-001?", cut=1)
        self.assertEqual(res.question_type, QuestionType.FACTUAL_RETRIEVAL)
        self.assertIn("STUDY042-101-001", res.direct_answer)
        self.assertIn("DM|STUDY042-101-001|1", res.evidence_references)
        self.assertGreater(len(res.supporting_records), 0)

    def test_04_rule_based_answer_via_rule_engine(self):
        """Verifies Rule Engine execution, finding derivation, and evidence references."""
        res = self.engine.answer("Are there any dosing errors at Cut 1?", cut=1)
        self.assertEqual(res.question_type, QuestionType.RULE_EVALUATION)
        self.assertIn("DOSING_ERROR", res.direct_answer)
        self.assertGreater(len(res.evidence_references), 0)
        self.assertIn("EX|STUDY042-102-002|1", res.evidence_references)

    def test_05_hybrid_answer_with_site_and_monitor_data(self):
        """Verifies integration of exact evidence, site reply, and monitor decision."""
        res = self.engine.answer("Why was subject STUDY042-101-002 flagged for SAE discrepancy and what did the monitor decide?", cut=1)
        self.assertEqual(res.question_type, QuestionType.HYBRID_MONITORING)
        self.assertIn("STUDY042-101-002", res.direct_answer)
        # Verify exact evidence identity
        self.assertIn("AE|STUDY042-101-002|1", res.evidence_references)
        # Verify site reply
        self.assertGreater(len(res.site_replies), 0)
        # Verify monitor decision (CLARIFY with inquiry)
        self.assertGreater(len(res.monitor_decisions), 0)
        self.assertEqual(res.monitor_decisions[0].get("decision"), "CLARIFY")

    def test_06_study_statistics_answer(self):
        """Verifies dynamic study statistics answering."""
        res = self.engine.answer("How many total subjects and sites are in the study at Cut 1?", cut=1)
        self.assertEqual(res.question_type, QuestionType.STUDY_STATISTICS)
        self.assertIn("enrolled subjects", res.direct_answer)
        self.assertIn("investigational sites", res.direct_answer)


if __name__ == "__main__":
    unittest.main()

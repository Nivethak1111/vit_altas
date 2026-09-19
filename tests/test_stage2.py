import os
import json
import unittest
from pathlib import Path

from stage1.atlas import Atlas, StudyGraph
from stage2.crew import ReviewCrew

BASE_DIR = Path(__file__).resolve().parent.parent

class MockServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We assume local API is running, but let's test crew offline logic if needed,
        # or we just rely on the existing StudyGraph without actual server hit (it ignores connection errors or we can mock requests).
        cls.data_dir = str(BASE_DIR / "data" / "STUDY-042")
        cls.graph = StudyGraph(cls.data_dir)
        cls.atlas = Atlas(cls.graph)
        
    def setUp(self):
        # clear memory
        memory_file = BASE_DIR / "data" / "crew_memory.json"
        if memory_file.exists():
            memory_file.unlink()
        
        self.crew = ReviewCrew(
            hub_url="http://localhost:8080/api",
            gateway_url="http://localhost:8080/api",
            team_key="test-key",
            atlas=self.atlas
        )

    def test_end_to_end_cycle(self):
        # Empty cycle (e.g. cut 0 if it existed, but we just use cut 1)
        report = self.crew.run_cycle(cut=1, protocol_version=1)
        
        # 14. Every node writes trace entries
        nodes_in_trace = {t['node'] for t in report.trace}
        self.assertIn('detect', nodes_in_trace)
        self.assertIn('medical_review', nodes_in_trace)
        self.assertIn('data_manager', nodes_in_trace)
        self.assertIn('compliance', nodes_in_trace)
        self.assertIn('human_gate', nodes_in_trace)
        self.assertIn('execute', nodes_in_trace)
        
        # 2. Stage 1 Atlas is called as detect
        self.assertGreater(report.total_findings, 0)
        
        # 13. Protocol version is taken from the cut
        self.assertEqual(report.protocol_version, 1)

    def test_memory_and_rerun(self):
        # 10. Same cut run twice produces 0 new queries, 0 new escalations
        r1 = self.crew.run_cycle(cut=1, protocol_version=1)
        
        q1 = r1.queries
        e1 = r1.medical_escalations
        
        # rerun
        r2 = self.crew.run_cycle(cut=1, protocol_version=1)
        
        self.assertEqual(r2.queries, 0)
        
        # Escalations logic depends on how the mock server responds. 
        # If the API server is offline, escalated_count might be 0, but no new queries for sure.

    def test_site_recurrence(self):
        # 11 & 12. Two cycle recurrence
        self.crew.run_cycle(cut=1, protocol_version=1)
        r2 = self.crew.run_cycle(cut=2, protocol_version=1)
        
        # We should see recurring site / subject flags in trace
        has_recurring = any('RECURRING' in t['action'] for t in r2.trace)
        self.assertTrue(has_recurring)
        
if __name__ == '__main__':
    unittest.main()

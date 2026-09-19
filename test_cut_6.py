import sys
import os
from stage1.atlas import StudyGraph
from services.finding_engine import FindingEngine

graph = StudyGraph("data/STUDY-042")
graph.build(cut=6)

engine = FindingEngine()
findings = engine.evaluate_study(graph._internal_graph, 6)

categories = {"safety": 0, "data": 0, "compliance": 0, "site": 0}

for f in findings:
    # Just printing them to understand
    print(f.finding_code, f.severity, f.domain, f.subject, f.rule_name)


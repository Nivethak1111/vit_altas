import os
import json
import time
from starter.schemas import Question
from stage1.atlas import StudyGraph, Atlas

def main():
    print("--- Starting Local Harness ---")
    data_dir = "data/STUDY-042"
    
    if not os.path.exists(data_dir):
        print(f"Warning: {data_dir} directory not found.")
        return
        
    # 1. Initialize StudyGraph
    print("Initializing StudyGraph...")
    start_time = time.time()
    graph = StudyGraph(data_dir)
    graph.build(cut=10) # Build up to cut 10
    build_ms = int((time.time() - start_time) * 1000)
    print(f"Graph built in {build_ms} ms.")
    
    # 2. Test Patient360
    # Let's dynamically get a valid subject from the graph to avoid SubjectNotFoundError
    subjects = graph._internal_graph.get_all_subjects(cut=10)
    valid_subject = subjects[0].usubjid if subjects else "UNKNOWN"
    
    print(f"\nTesting patient360 for {valid_subject}...")
    try:
        p360 = graph.patient360(valid_subject)
        print(f"Found domains: {list(p360.keys()) if p360 else 'None'}")
    except Exception as e:
        print(f"Error fetching patient 360: {e}")
    
    # 3. Initialize Atlas
    print("\nInitializing Atlas Answer Engine...")
    atlas = Atlas(graph)
    
    # 4. Test some queries
    questions = [
        Question(id="Q1", text="How many subjects have SAEs?"),
        Question(id="Q2", text="Show subjects with dosing errors."),
        Question(id="Q3", text="Find subjects meeting Hy's Law.")
    ]
    
    for q in questions:
        print(f"\nQ: {q.text}")
        ans = atlas.answer(q)
        print(f"Answer: {ans.answer}")
        print(f"Evidence: {[f'{e.domain}|{e.usubjid}|{e.seq}' for e in ans.evidence]}")
        print(f"Text: {ans.text}")

    print("\n--- Harness Complete ---")

if __name__ == "__main__":
    main()

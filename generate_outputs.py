import json
import time
import os
from stage1.atlas import StudyGraph, Atlas
from starter.schemas import Question

def generate_graph_stats(data_dir: str, cut: int):
    print("Generating graph_stats.json...")
    start_time = time.time()
    
    graph = StudyGraph(data_dir)
    graph.build(cut=cut)
    build_ms = int((time.time() - start_time) * 1000)
    
    # Introspect internal graph to get stats
    internal_g = graph._internal_graph
    
    subjects = internal_g.get_all_subjects(cut=cut)
    nodes_count = len(subjects)
    edges_count = 0
    for subj in subjects:
        # Just approximate edges based on records
        nodes_count += len(subj.records) if hasattr(subj, 'records') else 0
        edges_count += len(subj.records) if hasattr(subj, 'records') else 0
            
    stats = {
        "nodes": nodes_count,
        "edges": edges_count,
        "subjects": len(subjects),
        "build_ms": build_ms,
        "cut": cut
    }
    
    with open("graph_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print("Saved graph_stats.json")
    return graph

def generate_stage1_public(graph: StudyGraph):
    print("Generating stage1_public.json...")
    atlas = Atlas(graph)
    
    # 10 mock public questions based on typical requirements
    questions = [
        Question(id="Q1", text="How many subjects have SAEs?"),
        Question(id="Q2", text="Show subjects with dosing errors."),
        Question(id="Q3", text="Find subjects meeting Hy's Law criteria."),
        Question(id="Q4", text="How many missing values are there in the AE domain?"),
        Question(id="Q5", text="What is the treatment of SUBJ-001?"),
        Question(id="Q6", text="How many findings exist at cut 3?"),
        Question(id="Q7", text="Show subjects taking prohibited medications."),
        Question(id="Q8", text="Did SUBJ-001 have a serious AE?"),
        Question(id="Q9", text="Show duplicate subjects."),
        Question(id="Q10", text="How many subjects dropped out due to adverse events? (TRAP)")
    ]
    
    results = []
    for q in questions:
        ans = atlas.answer(q)
        results.append({
            "question_id": ans.question_id,
            "answer": ans.answer,
            "text": ans.text,
            "evidence": [{"domain": e.domain, "usubjid": e.usubjid, "seq": e.seq} for e in ans.evidence]
        })
        
    with open("stage1_public.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved stage1_public.json")

if __name__ == "__main__":
    data_dir = "data/STUDY-042"
    cut = 3
    if os.path.exists(data_dir):
        g = generate_graph_stats(data_dir, cut)
        generate_stage1_public(g)
    else:
        print("Data directory not found. Create 'data' folder to generate stats.")

import os
from stage1.atlas import StudyGraph, Atlas
from stage2.crew import ReviewCrew

def main():
    graph = StudyGraph("data/STUDY-042")
    atlas = Atlas(graph)
    
    # Normally hub_url and gateway_url would be real endpoints.
    # For local test, they might fail to connect.
    crew = ReviewCrew("http://localhost:8080", "http://localhost:8080/api", "dummy-key", atlas)
    
    report = crew.run_cycle(cut=6, protocol_version=2)
    
    print("\n--- Review Report Trace ---")
    for line in report.trace:
        print(line)

if __name__ == "__main__":
    main()

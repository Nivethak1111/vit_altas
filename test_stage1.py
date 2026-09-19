import os
from stage1.atlas import StudyGraph, Atlas
from starter.schemas import Question

def main():
    graph = StudyGraph("data/STUDY-042")
    res_build = graph.build(cut=1)
    print("Build stats:", res_build)
    
    atlas = Atlas(graph)
    
    print("\n-- TEST B & C: Count questions --")
    q1 = Question(id="q1", text="How many subjects have SAEs?")
    ans1 = atlas.answer(q1)
    print("Count Q1 answer:", ans1.answer, type(ans1.answer))
    
    q2 = Question(id="q2", text="How many subjects have NONEXISTENT_DISEASE?")
    ans2 = atlas.answer(q2)
    print("Zero Count answer:", ans2.answer, type(ans2.answer))
    
    print("\n-- TEST D: Trap question --")
    q3 = Question(id="q3", text="Which subjects have NONEXISTENT_DISEASE?")
    ans3 = atlas.answer(q3)
    print("Trap answer:", ans3.answer, type(ans3.answer))
    
    print("\n-- TEST E: Evidence format --")
    q4 = Question(id="q4", text="Which subjects have SAEs?")
    ans4 = atlas.answer(q4)
    print("Evidence:")
    for ev in ans4.evidence[:3]:
        print(f"Domain={ev.domain}, Subject={ev.usubjid}, Seq={ev.seq}")
        
    print("\n-- TEST F: Cut switching --")
    q_dose = Question(id="q5", text="Show subjects with dosing errors.")
    graph.build(cut=1)
    ans_dose1 = atlas.answer(q_dose)
    print("Cut 1 dosing error findings count:", len(ans_dose1.evidence))
    
    graph.build(cut=2)
    ans_dose2 = atlas.answer(q_dose)
    print("Cut 2 dosing error findings count:", len(ans_dose2.evidence))
    
    print("\n-- TEST G: Patient360 --")
    p360 = graph.patient360("STUDY042-101-002")
    print("Patient360 USUBJID:", p360.get("usubjid"))
    
if __name__ == "__main__":
    main()

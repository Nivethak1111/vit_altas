"""
Patient 360 Service
Aggregates a complete, cut-aware clinical view of a single subject directly from StudyGraph:
- Demographics
- Site info
- Treatment / Exposure history
- Adverse Events & Serious Adverse Events
- Laboratory Results (with lab-specific ranges, units, and interpretations)
- Vital Signs
- Concomitant Medications
- Medical History
- ECG Findings
- Disposition
- Detected Findings & Evidence References
Zero hard-coding!
"""
from typing import Any, Dict, List, Optional
from graph.study_graph import StudyGraph
from services.finding_engine import FindingEngine
from utils.errors import SubjectNotFoundError


class Patient360Service:
    def __init__(self, finding_engine: Optional[FindingEngine] = None):
        self.finding_engine = finding_engine or FindingEngine()

    def get_patient_profile(self, graph: StudyGraph, usubjid: str, cut: int) -> Dict[str, Any]:
        """
        Builds full Patient 360 profile at requested cut N.
        """
        clean_id = str(usubjid).strip()
        subject = graph.get_subject(clean_id, cut=cut)

        protocol_version = graph.get_protocol_for_cut(cut)

        # 1. Demographics
        demo_rec = subject.demographics
        demographics = demo_rec.to_dict() if demo_rec else {}

        # 2. Exposure
        ex_recs = subject.get_exposure(cut)
        exposure = [r.to_dict() for r in ex_recs]

        # 3. Adverse Events & SAEs
        ae_recs = subject.get_adverse_events(cut)
        all_aes = []
        serious_aes = []

        for ae in ae_recs:
            ae_dict = ae.to_dict()
            aeser = str(ae.get("AESER", "")).upper()
            aeshosp = str(ae.get("AESHOSP", "")).upper()
            aesdth = str(ae.get("AESDTH", "")).upper()
            aeslife = str(ae.get("AESLIFE", "")).upper()

            is_serious = (aeser == "Y") or (aeshosp == "Y") or (aesdth == "Y") or (aeslife == "Y")
            ae_dict["is_serious"] = is_serious
            ae_dict["discrepancy"] = (aeshosp == "Y" and aeser != "Y")
            all_aes.append(ae_dict)
            if is_serious:
                serious_aes.append(ae_dict)

        # 4. Laboratory results with lab interpretations
        lb_recs = subject.get_laboratory_results(cut)
        laboratory_results = []
        for lb in lb_recs:
            interp = graph.interpret_lab_record(lb)
            lb_dict = lb.to_dict()
            lb_dict["interpretation"] = interp.to_dict()
            laboratory_results.append(lb_dict)

        # 5. Vital Signs
        vs_recs = subject.get_vital_signs(cut)
        vital_signs = [r.to_dict() for r in vs_recs]

        # 6. Concomitant Medications
        cm_recs = subject.get_medications(cut)
        concomitant_medications = [r.to_dict() for r in cm_recs]

        # 7. Medical History
        mh_recs = subject.get_medical_history(cut)
        medical_history = [r.to_dict() for r in mh_recs]

        # 8. ECG
        eg_recs = subject.get_ecg(cut)
        ecg_records = [r.to_dict() for r in eg_recs]

        # 9. Disposition
        ds_recs = subject.get_disposition(cut)
        disposition = [r.to_dict() for r in ds_recs]

        # 10. Detected Findings for this subject
        findings = self.finding_engine.evaluate_subject(graph, clean_id, cut)
        findings_dicts = [f.to_dict() for f in findings]

        # 11. Evidence References
        evidence_references = []
        for domain, recs in subject.records_by_domain.items():
            for r in recs:
                if r.cut_available <= cut:
                    evidence_references.append(str(r.identity))

        return {
            "usubjid": clean_id,
            "site_id": subject.site_id,
            "cut": cut,
            "protocol_version": protocol_version,
            "demographics": demographics,
            "exposure": exposure,
            "adverse_events": all_aes,
            "serious_adverse_events": serious_aes,
            "laboratory_results": laboratory_results,
            "vital_signs": vital_signs,
            "concomitant_medications": concomitant_medications,
            "medical_history": medical_history,
            "ecg": ecg_records,
            "disposition": disposition,
            "findings": findings_dicts,
            "evidence_references": evidence_references,
            "total_records_at_cut": len(evidence_references),
        }

"""
StudyGraph Node Models: Study, Site, and Subject Nodes
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from models.study_record import DomainRecord


@dataclass
class SubjectNode:
    usubjid: str
    site_id: str
    records_by_domain: Dict[str, List[DomainRecord]] = field(default_factory=dict)
    demographics: Optional[DomainRecord] = None
    graph: Optional[Any] = None

    def add_record(self, record: DomainRecord):
        domain = record.domain.upper()
        if domain not in self.records_by_domain:
            self.records_by_domain[domain] = []
        self.records_by_domain[domain].append(record)
        if domain == "DM":
            self.demographics = record
            site_from_dm = record.get("SITEID") or record.get("SITE")
            if site_from_dm:
                self.site_id = site_from_dm

    def get_records(self, domain: str, cut: Optional[int] = None) -> List[DomainRecord]:
        domain = domain.upper()
        recs = self.records_by_domain.get(domain, [])
        if cut is not None:
            available = [r for r in recs if r.cut_available <= cut]
        else:
            available = list(recs)

        if self.graph and hasattr(self.graph, "correction_service"):
            return [self.graph.correction_service.apply_corrections_to_record(r, cut) for r in available]
        return available

    def get_adverse_events(self, cut: Optional[int] = None) -> List[DomainRecord]:
        return self.get_records("AE", cut)

    def get_laboratory_results(self, cut: Optional[int] = None) -> List[DomainRecord]:
        return self.get_records("LB", cut)

    def get_exposure(self, cut: Optional[int] = None) -> List[DomainRecord]:
        return self.get_records("EX", cut)

    def get_medications(self, cut: Optional[int] = None) -> List[DomainRecord]:
        return self.get_records("CM", cut)

    def get_vital_signs(self, cut: Optional[int] = None) -> List[DomainRecord]:
        return self.get_records("VS", cut)

    def get_ecg(self, cut: Optional[int] = None) -> List[DomainRecord]:
        return self.get_records("EG", cut)

    def get_medical_history(self, cut: Optional[int] = None) -> List[DomainRecord]:
        return self.get_records("MH", cut)

    def get_disposition(self, cut: Optional[int] = None) -> List[DomainRecord]:
        return self.get_records("DS", cut)

    def to_dict(self, cut: Optional[int] = None) -> Dict[str, Any]:
        domain_counts = {}
        for d, recs in self.records_by_domain.items():
            if cut is not None:
                domain_counts[d] = sum(1 for r in recs if r.cut_available <= cut)
            else:
                domain_counts[d] = len(recs)

        demo_dict = self.demographics.to_dict() if self.demographics else {}
        return {
            "usubjid": self.usubjid,
            "site_id": self.site_id,
            "demographics": demo_dict,
            "domain_counts": domain_counts,
        }


@dataclass
class SiteNode:
    site_id: str
    subjects: List[str] = field(default_factory=list)

    def add_subject(self, usubjid: str):
        if usubjid not in self.subjects:
            self.subjects.append(usubjid)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "subject_count": len(self.subjects),
            "subjects": self.subjects,
        }


@dataclass
class StudyNode:
    study_id: str
    sites: Dict[str, SiteNode] = field(default_factory=dict)
    protocol_versions_by_cut: Dict[int, str] = field(default_factory=dict)
    available_cuts: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "study_id": self.study_id,
            "sites": [s.to_dict() for s in self.sites.values()],
            "protocol_versions_by_cut": self.protocol_versions_by_cut,
            "available_cuts": sorted(self.available_cuts),
        }

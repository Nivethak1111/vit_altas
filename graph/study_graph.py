"""
StudyGraph Data Model and Graph Traversal Engine
Represents hierarchical clinical relationships:
Study -> Protocol Versions -> Data Cuts -> Sites -> Subjects -> Clinical Domains
Provides exact evidence retrieval (domain, USUBJID, SEQ),
cut-aware views, non-destructive correction resolution, and full multi-domain traversal.
"""
from typing import Any, Dict, List, Optional, Tuple

from models.corrections import FieldCorrection
from models.documents import StudyDocument
from models.graph_nodes import SiteNode, StudyNode, SubjectNode
from models.reference_range import LabReferenceRange
from models.study_record import DomainRecord, EvidenceIdentity
from services.correction_service import CorrectionService
from services.cut_manager import CutManager, CutMetadata
from services.ingestion_service import IngestionService
from services.lab_service import LabInterpretation, LabSafetyService
from services.response_service import ResponseService
from utils.errors import RecordNotFoundError, SubjectNotFoundError


class StudyGraph:
    def __init__(self, study_id: str = "DEFAULT"):
        self.study_id = study_id
        self.study_node = StudyNode(study_id=study_id)
        self.cut_manager = CutManager()
        self.correction_service = CorrectionService()
        self.lab_service = LabSafetyService()
        self.response_service = ResponseService()

        # Evidence index: (domain.upper(), usubjid, int(seq)) -> DomainRecord
        self._record_index: Dict[Tuple[str, str, int], DomainRecord] = {}

        # Subject index: usubjid -> SubjectNode
        self._subjects: Dict[str, SubjectNode] = {}

        # Site index: site_id -> SiteNode
        self._sites: Dict[str, SiteNode] = {}

        # Documents: name -> StudyDocument
        self._documents: Dict[str, StudyDocument] = {}

    @classmethod
    def load_study(cls, study_dir: str) -> "StudyGraph":
        """
        Loads all study files from study_dir and constructs the full StudyGraph.
        """
        raw_data = IngestionService.load_study_data(study_dir)
        graph = cls(study_id=raw_data["study_id"])

        # Cuts
        for c in raw_data["cuts"]:
            graph.cut_manager.add_cut(c)
            graph.study_node.protocol_versions_by_cut[c.cut_id] = c.protocol_version
            graph.study_node.available_cuts.append(c.cut_id)

        # Corrections
        for corr in raw_data["corrections"]:
            graph.correction_service.add_correction(corr)

        # Reference ranges
        for rr in raw_data["reference_ranges"]:
            graph.lab_service.add_reference_range(rr)

        # Responses
        graph.response_service = ResponseService(
            site_replies_raw=raw_data["site_replies"],
            monitor_decisions_raw=raw_data["monitor_decisions"],
        )

        # Documents
        for doc in raw_data["documents"]:
            graph._documents[doc.name] = doc

        # Clinical records by domain
        for domain, records in raw_data["records_by_domain"].items():
            for rec in records:
                graph.add_record(rec)

        return graph

    def add_record(self, record: DomainRecord):
        """Indexes a domain record and connects it to Subject and Site nodes."""
        usubjid = str(record.usubjid).strip()
        if not usubjid:
            return

        domain = record.domain.upper().strip()
        seq = int(record.seq)
        key = (domain, usubjid, seq)
        self._record_index[key] = record

        # Determine site ID
        raw_site = (
            record.get("SITEID")
            or record.get("SITE")
            or record.get("STUDYSITE")
            or (usubjid.split("-")[1] if "-" in usubjid and len(usubjid.split("-")) >= 2 else "SITE-01")
        )
        site_id = str(raw_site).strip()
        if site_id and not site_id.upper().startswith("SITE-"):
            site_id = f"SITE-{site_id}"

        # Site Node
        if site_id not in self._sites:
            site_node = SiteNode(site_id=site_id)
            self._sites[site_id] = site_node
            self.study_node.sites[site_id] = site_node
        self._sites[site_id].add_subject(usubjid)

        # Subject Node
        if usubjid not in self._subjects:
            self._subjects[usubjid] = SubjectNode(usubjid=usubjid, site_id=site_id, graph=self)
        else:
            self._subjects[usubjid].graph = self
            if domain == "DM":
                self._subjects[usubjid].site_id = site_id
        self._subjects[usubjid].add_record(record)

    def get_subject(self, usubjid: str, cut: Optional[int] = None) -> SubjectNode:
        """Retrieves a SubjectNode by USUBJID."""
        clean_id = str(usubjid).strip()
        if clean_id not in self._subjects:
            raise SubjectNotFoundError(f"Subject not found: {usubjid}")
        return self._subjects[clean_id]

    def get_site(self, site_id: str, cut: Optional[int] = None) -> SiteNode:
        """Retrieves a SiteNode by site_id."""
        clean_id = str(site_id).strip()
        if clean_id not in self._sites:
            # Fallback or create empty
            return SiteNode(site_id=clean_id, subjects=[])
        return self._sites[clean_id]

    def get_all_subjects(self, cut: Optional[int] = None) -> List[SubjectNode]:
        """Returns all subjects who have at least one record available at the requested cut."""
        if cut is None:
            return list(self._subjects.values())
        active = []
        for s in self._subjects.values():
            # Check if any record has cut_available <= cut
            has_records = any(
                any(r.cut_available <= cut for r in recs)
                for recs in s.records_by_domain.values()
            )
            if has_records:
                active.append(s)
        return active

    def get_all_sites(self) -> List[SiteNode]:
        return list(self._sites.values())

    def get_record(
        self, domain: str, usubjid: str, seq: int, cut: Optional[int] = None
    ) -> DomainRecord:
        """
        Retrieves exact record using Evidence Identity: (domain, USUBJID, DOMAINSEQ).
        Applies non-destructive corrections for the requested cut.
        """
        key = (domain.upper().strip(), str(usubjid).strip(), int(seq))
        rec = self._record_index.get(key)
        if not rec:
            raise RecordNotFoundError(f"Record not found: domain={domain}, usubjid={usubjid}, seq={seq}")

        # Check cut availability
        if cut is not None and rec.cut_available > cut:
            raise RecordNotFoundError(
                f"Record not available at cut {cut} (available at cut {rec.cut_available})"
            )

        # Apply cut-specific corrections
        return self.correction_service.apply_corrections_to_record(rec, cut)

    def get_records(
        self,
        domain: str,
        cut: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[DomainRecord]:
        """Returns all records for a domain, filtered by cut and optional field conditions."""
        domain_upper = domain.upper().strip()
        results = []
        for (d, _, _), rec in self._record_index.items():
            if d != domain_upper:
                continue
            if cut is not None and rec.cut_available > cut:
                continue

            evaluated_rec = self.correction_service.apply_corrections_to_record(rec, cut)

            # Apply filters
            if filters:
                match = True
                for k, v in filters.items():
                    if str(evaluated_rec.get(k, "")).lower() != str(v).lower():
                        match = False
                        break
                if not match:
                    continue

            results.append(evaluated_rec)
        return sorted(results, key=lambda r: (r.usubjid, r.seq))

    def get_records_at_cut(self, cut: int) -> Dict[str, List[DomainRecord]]:
        """Returns all study records grouped by domain that are available at cut N."""
        domains: Dict[str, List[DomainRecord]] = {}
        for (d, _, _), rec in self._record_index.items():
            if rec.cut_available <= cut:
                if d not in domains:
                    domains[d] = []
                domains[d].append(self.correction_service.apply_corrections_to_record(rec, cut))
        return domains

    def get_protocol_for_cut(self, cut: int) -> str:
        """Determines active protocol version for the given cut."""
        return self.cut_manager.get_protocol_for_cut(cut)

    def get_reference_range(
        self, lab: str, test: str, cut: Optional[int] = None
    ) -> Optional[LabReferenceRange]:
        return self.lab_service.get_reference_range(lab, test)

    def get_correction(
        self, domain: str, usubjid: str, seq: int, cut: Optional[int] = None
    ) -> Optional[FieldCorrection]:
        return self.correction_service.get_latest_correction(domain, usubjid, seq, cut)

    def get_site_reply(self, domain: str, usubjid: str, seq: int) -> Dict[str, Any]:
        return self.response_service.get_site_reply(domain, usubjid, seq)

    def get_monitor_decision(self, code: str, usubjid: str) -> Optional[Dict[str, Any]]:
        return self.response_service.get_monitor_decision(code, usubjid)

    def get_document(self, name: str) -> Optional[StudyDocument]:
        return self._documents.get(name)

    def get_all_documents(self) -> List[StudyDocument]:
        return list(self._documents.values())

    def interpret_lab_record(self, record: DomainRecord) -> LabInterpretation:
        return self.lab_service.evaluate_record(record)

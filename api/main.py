"""
ATLAS / Study Sentinel - Clinical Trial Monitoring Platform Server
Zero-dependency, production-grade HTTP REST API & Static File Server.
Uses Python Standard Library (http.server, urllib.parse, json).
"""
import json
import mimetypes
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from graph.graph_statistics import GraphStatistics
from graph.study_graph import StudyGraph
from services.answer_engine import AnswerEngine
from services.finding_engine import FindingEngine
from services.ingestion_service import IngestionService
from services.patient360_service import Patient360Service
from utils.errors import AtlasError, RecordNotFoundError, SubjectNotFoundError


class StudyCache:
    """Caches loaded StudyGraph instances per study directory."""
    def __init__(self, data_root: Path):
        self.data_root = data_root
        self._graphs = {}
        self.finding_engine = FindingEngine()
        self.patient360_service = Patient360Service(self.finding_engine)

    def get_study(self, study_id: str) -> StudyGraph:
        if study_id not in self._graphs:
            study_dir = self.data_root / study_id
            if not study_dir.exists():
                # Fallback to first available study
                available = IngestionService.find_studies(str(self.data_root))
                if available:
                    study_id = available[0]
                    study_dir = self.data_root / study_id
                else:
                    raise FileNotFoundError(f"Study '{study_id}' not found in {self.data_root}")
            graph = StudyGraph.load_study(str(study_dir))
            self._graphs[study_id] = graph
        return self._graphs[study_id]

    def get_answer_engine(self, study_id: str) -> AnswerEngine:
        graph = self.get_study(study_id)
        return AnswerEngine(graph, self.finding_engine)

    def list_studies(self):
        return IngestionService.find_studies(str(self.data_root))


# Global Cache instance
DATA_DIR = BASE_DIR / "data"
CACHE = StudyCache(DATA_DIR)


class AtlasRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS and disable caching for API
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Helper to get first query param
        def q(key, default=""):
            return query.get(key, [default])[0]

        # REST API Router
        if path.startswith("/api/"):
            try:
                self.handle_api(path, q)
            except Exception as e:
                self.send_json({"error": str(e), "type": type(e).__name__}, status=500)
            return

        # Static files fallback to web/ or static/
        static_dir = BASE_DIR / "web"
        if not static_dir.exists():
            static_dir = BASE_DIR / "static"

        rel_path = path.lstrip("/")
        if not rel_path or rel_path == "":
            rel_path = "index.html"

        file_path = static_dir / rel_path
        if file_path.exists() and file_path.is_file():
            self.serve_file(file_path)
        else:
            # Fallback to index.html for SPA routing
            index_path = static_dir / "index.html"
            if index_path.exists():
                self.serve_file(index_path)
            else:
                self.send_error(404, f"File not found: {path}")

    def handle_api(self, path: str, q):
        study_id = q("study", "STUDY-042")
        cut_str = q("cut", "")
        cut = int(cut_str) if cut_str.isdigit() else None

        # 1. Studies List
        if path == "/api/studies":
            studies = CACHE.list_studies()
            self.send_json({"studies": studies, "current": study_id})
            return

        graph = CACHE.get_study(study_id)
        if cut is None:
            cuts = graph.cut_manager.get_available_cuts()
            cut = cuts[-1] if cuts else 1

        # 2. Cuts
        if path == "/api/cuts":
            cuts_meta = [c.to_dict() for c in graph.cut_manager.get_all_cuts()]
            self.send_json({
                "study_id": study_id,
                "cuts": cuts_meta,
                "active_cut": cut,
                "protocol_version": graph.get_protocol_for_cut(cut),
            })
            return

        # 3. Dynamic Statistics
        if path == "/api/statistics":
            stats = GraphStatistics.calculate(graph, cut=cut)
            self.send_json(stats)
            return

        # 4. Subjects
        if path == "/api/subjects":
            active_subjects = graph.get_all_subjects(cut=cut)
            site_filter = q("site")
            subjects_data = []
            for s in active_subjects:
                if site_filter and s.site_id != site_filter:
                    continue
                subjects_data.append(s.to_dict(cut=cut))
            self.send_json({"study_id": study_id, "cut": cut, "subjects": subjects_data})
            return

        # 5. Patient 360
        if path == "/api/patient360":
            subject_id = q("subject")
            if not subject_id:
                self.send_json({"error": "Missing 'subject' query parameter"}, status=400)
                return
            profile = CACHE.patient360_service.get_patient_profile(graph, subject_id, cut=cut)
            self.send_json(profile)
            return

        # 6. Findings
        if path == "/api/findings":
            filters = {}
            for param in ["site", "subject", "domain", "severity", "status", "finding_code"]:
                val = q(param)
                if val:
                    filters[param] = val
            findings = CACHE.finding_engine.evaluate_study(graph, cut=cut, filters=filters)
            self.send_json({
                "study_id": study_id,
                "cut": cut,
                "protocol_version": graph.get_protocol_for_cut(cut),
                "total_findings": len(findings),
                "findings": [f.to_dict() for f in findings],
            })
            return

        # 7. Study Graph View
        if path == "/api/graph":
            subject_id = q("subject")
            if not subject_id:
                # Study-level sites and subject graph nodes
                nodes = [{"id": study_id, "type": "study", "label": f"Study {study_id}"}]
                links = []
                for site in graph.get_all_sites():
                    nodes.append({"id": site.site_id, "type": "site", "label": site.site_id})
                    links.append({"source": study_id, "target": site.site_id})
                self.send_json({"nodes": nodes, "links": links})
                return

            subject = graph.get_subject(subject_id, cut=cut)
            # Build Subject -> Domain Nodes
            nodes = [
                {
                    "id": subject.usubjid,
                    "type": "subject",
                    "label": subject.usubjid,
                    "site_id": subject.site_id,
                    "arm": subject.demographics.get("ARM") if subject.demographics else "Unknown",
                }
            ]
            links = []
            for domain, recs in subject.records_by_domain.items():
                avail_recs = [r for r in recs if r.cut_available <= cut]
                if avail_recs:
                    dom_id = f"{subject.usubjid}_{domain}"
                    nodes.append({
                        "id": dom_id,
                        "type": "domain",
                        "domain": domain,
                        "label": f"{domain} ({len(avail_recs)})",
                        "count": len(avail_recs),
                    })
                    links.append({"source": subject.usubjid, "target": dom_id})

            self.send_json({"subject": subject.to_dict(cut=cut), "nodes": nodes, "links": links})
            return

        # 8. Exact Record Lookup: (domain, usubjid, seq, cut)
        if path == "/api/record":
            domain = q("domain")
            usubjid = q("usubjid")
            seq_str = q("seq")
            if not (domain and usubjid and seq_str.isdigit()):
                self.send_json({"error": "domain, usubjid, and seq required"}, status=400)
                return
            rec = graph.get_record(domain, usubjid, int(seq_str), cut=cut)
            rec_dict = rec.to_dict()
            if domain.upper() == "LB":
                rec_dict["interpretation"] = graph.interpret_lab_record(rec).to_dict()
            self.send_json(rec_dict)
            return

        # 9. Responses & Decisions
        if path == "/api/responses":
            replies = graph.response_service._site_replies
            decisions = graph.response_service._monitor_decisions
            self.send_json({"site_replies": replies, "monitor_decisions": decisions})
            return

        # 10. Documents
        if path == "/api/documents":
            doc_name = q("name")
            if doc_name:
                doc = graph.get_document(doc_name)
                if doc:
                    self.send_json(doc.to_dict())
                else:
                    self.send_json({"error": f"Document '{doc_name}' not found"}, status=404)
            else:
                docs = [d.to_dict() for d in graph.get_all_documents()]
                self.send_json({"documents": docs})
            return

        # 11. Answer Engine Query Endpoint (USER QUESTION -> Query Understanding -> Question Type -> StudyGraph / Rule Engine -> Evidence -> Site/Monitor -> Answer)
        if path == "/api/query":
            question = q("question") or q("q")
            if not question:
                self.send_json({"error": "Missing 'question' parameter"}, status=400)
                return
            engine = CACHE.get_answer_engine(study_id)
            answer_res = engine.answer(question, cut=cut)
            self.send_json(answer_res.to_dict())
            return

        # 12. Global Search
        if path == "/api/search":
            query_str = q("q", "").lower()
            results = []
            if query_str:
                # Search Subjects
                for s in graph.get_all_subjects(cut=cut):
                    if query_str in s.usubjid.lower() or query_str in s.site_id.lower():
                        results.append({"type": "subject", "id": s.usubjid, "site": s.site_id})
                # Search Findings
                all_findings = CACHE.finding_engine.evaluate_study(graph, cut=cut)
                for f in all_findings:
                    if query_str in f.finding_code.lower() or query_str in f.domain.lower() or any(query_str in str(ev).lower() for ev in f.evidence_references):
                        results.append({"type": "finding", "id": f.finding_code, "subject": f.subject, "domain": f.domain})
                # Search Evidence (Identity: DOMAIN|USUBJID|SEQ)
                for (d, subj, seq), rec in graph._record_index.items():
                    if rec.cut_available <= cut:
                        ident = f"{d}|{subj}|{seq}".lower()
                        if query_str in ident or query_str in d.lower():
                            results.append({"type": "evidence", "id": f"{d}|{subj}|{seq}", "domain": d, "subject": subj})
            self.send_json({"query": query_str, "results": results[:50]})
            return

        # 13. Lab Explorer
        if path == "/api/labs":
            subject_filter = q("subject")
            site_filter = q("site")
            test_filter = q("test")
            lab_filter = q("lab")
            labs_data = []
            
            for (d, subj, seq), rec in graph._record_index.items():
                if d == "LB" and rec.cut_available <= cut:
                    if subject_filter and subj != subject_filter:
                        continue
                    # get subject node for site
                    subj_node = graph.get_subject(subj, cut=cut)
                    if site_filter and (not subj_node or subj_node.site_id != site_filter):
                        continue
                    
                    fields = rec.fields
                    test_code = fields.get("LBTESTCD") or fields.get("LBTEST") or ""
                    if test_filter and test_filter.lower() not in test_code.lower():
                        continue
                    lab_name = fields.get("LBNAM") or ""
                    if lab_filter and lab_filter.lower() not in lab_name.lower():
                        continue
                        
                    interp = graph.interpret_lab_record(rec)
                    labs_data.append({
                        "subject": subj,
                        "site": subj_node.site_id if subj_node else "",
                        "test": test_code,
                        "reported_value": fields.get("LBORRES"),
                        "reported_unit": fields.get("LBORRESU"),
                        "normalized_value": interp.normalized_value,
                        "normalized_unit": interp.normalized_unit,
                        "ref_low": interp.ref_low,
                        "ref_high": interp.ref_high,
                        "lab": lab_name,
                        "date": fields.get("LBDTC"),
                        "evidence": f"LB|{subj}|{seq}"
                    })
            self.send_json({"labs": labs_data})
            return

        # 14. Cut Comparison
        if path == "/api/compare_cuts":
            cut_n = int(q("cut_n", 1))
            cut_m = int(q("cut_m", 2))
            
            n_stats = GraphStatistics.calculate(graph, cut=cut_n)
            m_stats = GraphStatistics.calculate(graph, cut=cut_m)
            
            # Find new records
            new_records = []
            for (d, subj, seq), rec in graph._record_index.items():
                if cut_n < rec.cut_available <= cut_m:
                    new_records.append(f"{d}|{subj}|{seq}")
            
            # Find corrected records
            corrected_records = []
            for (d, subj, seq), corrs in graph.correction_service._corrections.items():
                for c in corrs:
                    if cut_n < c.correction_cut <= cut_m:
                        corrected_records.append({"evidence": f"{d}|{subj}|{seq}", "field": c.field_name, "old": c.original_value, "new": c.corrected_value})
            
            # Find findings differences
            n_findings = CACHE.finding_engine.evaluate_study(graph, cut=cut_n)
            m_findings = CACHE.finding_engine.evaluate_study(graph, cut=cut_m)
            
            n_find_keys = {f"{f.finding_code}|{f.subject}" for f in n_findings}
            m_find_keys = {f"{f.finding_code}|{f.subject}" for f in m_findings}
            
            new_findings = list(m_find_keys - n_find_keys)
            resolved_findings = list(n_find_keys - m_find_keys)
            
            self.send_json({
                "cut_n": cut_n,
                "cut_m": cut_m,
                "protocol_n": n_stats["protocol_version"],
                "protocol_m": m_stats["protocol_version"],
                "new_records": new_records,
                "corrected_records": corrected_records,
                "new_findings": new_findings,
                "resolved_findings": resolved_findings
            })
            return

        # 15. Stage 2 GET Endpoints
        if path == "/api/cycle_report":
            # Just serve the latest report saved by ReviewCrew
            store_path = BASE_DIR / "data" / "cycle_report.json"
            if store_path.exists():
                with open(store_path, "r") as f:
                    self.send_json(json.load(f))
            else:
                self.send_json({"error": "No cycle report found"}, status=404)
            return
            
        if path == "/api/trace":
            store_path = BASE_DIR / "data" / "trace.json"
            if store_path.exists():
                with open(store_path, "r") as f:
                    self.send_json({"trace": json.load(f)})
            else:
                self.send_json({"trace": []})
            return
            
        if path == "/api/queries_list": # Re-mapped to avoid conflict with /api/query which is POST
            store_path = BASE_DIR / "data" / "queries_store.json"
            if store_path.exists():
                with open(store_path, "r") as f:
                    self.send_json({"queries": json.load(f)})
            else:
                self.send_json({"queries": []})
            return
            
        if path == "/api/pending_escalations":
            store_path = BASE_DIR / "data" / "escalations_store.json"
            if store_path.exists():
                with open(store_path, "r") as f:
                    escs = json.load(f)
                    pending = {k: v for k, v in escs.items() if v.get("decision") == "CLARIFY"}
                    self.send_json({"pending": pending})
            else:
                self.send_json({"pending": {}})
            return
            
        if path == "/api/memory":
            store_path = BASE_DIR / "data" / "crew_memory.json"
            if store_path.exists():
                with open(store_path, "r") as f:
                    self.send_json(json.load(f))
            else:
                self.send_json({"memory": {}})
            return

        self.send_error(404, f"API endpoint not found: {path}")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        try:
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            data = {}
            
        if path == "/api/query":
            question = data.get("question") or data.get("q", "")
            study_id = data.get("study", "STUDY-042")
            cut = data.get("cut")
            if cut is not None:
                try:
                    cut = int(cut)
                except ValueError:
                    cut = None
            engine = CACHE.get_answer_engine(study_id)
            res = engine.answer(question, cut=cut)
            self.send_json(res.to_dict())
            return
            
        elif path == "/api/queries":
            # Data Manager POSTs queries here
            # Append to a file-backed store
            store_path = BASE_DIR / "data" / "queries_store.json"
            queries = []
            if store_path.exists():
                with open(store_path, "r") as f:
                    try: queries = json.load(f)
                    except: pass
            
            # Simple identity check
            new_id = f"Q-{len(queries)+1:04d}"
            query_record = {
                "id": new_id,
                "usubjid": data.get("usubjid"),
                "domain": data.get("domain"),
                "seq": data.get("seq"),
                "cut": data.get("cut"),
                "text": data.get("text"),
                "status": "OPEN"
            }
            queries.append(query_record)
            with open(store_path, "w") as f:
                json.dump(queries, f, indent=2)
            
            self.send_json({"status": "created", "query": query_record})
            return
            
        elif path == "/api/escalations":
            # Human Gate POSTs escalations here
            store_path = BASE_DIR / "data" / "escalations_store.json"
            escalations = {}
            if store_path.exists():
                with open(store_path, "r") as f:
                    try: escalations = json.load(f)
                    except: pass
                    
            code = data.get("code", "")
            usubjid = data.get("usubjid", "")
            escalation_key = f"{code}|{usubjid}"
            
            if escalation_key not in escalations:
                escalations[escalation_key] = {"count": 1, "history": [data]}
            else:
                escalations[escalation_key]["count"] += 1
                escalations[escalation_key]["history"].append(data)
                
            count = escalations[escalation_key]["count"]
            
            # Simulate monitor replies based on count and code
            if "SAE" in code or "HYS_LAW" in code:
                if count == 1:
                    decision = "CLARIFY"
                    reason = "What was the ALT at screening, and is there a concomitant hepatotoxic medication?" if "HYS_LAW" in code else "Please provide more details from the source record."
                else:
                    decision = "APPROVED"
                    reason = "Action approved after clarification."
            else:
                decision = "REJECTED" if count % 2 == 0 else "APPROVED"
                reason = "Routine decision"
                
            escalations[escalation_key]["decision"] = decision
            escalations[escalation_key]["reason"] = reason
            
            with open(store_path, "w") as f:
                json.dump(escalations, f, indent=2)
                
            self.send_json({"id": f"E-{len(escalations):04d}", "decision": decision, "reason": reason})
            return
            
            
        elif path == "/api/run_cycle":
            cut = data.get("cut", 1)
            study_id = data.get("study", "STUDY-042")
            graph = CACHE.get_study(study_id)
            protocol_version = graph.get_protocol_for_cut(cut)
            # ensure integer
            if isinstance(protocol_version, str):
                try: protocol_version = int(protocol_version.replace('V', '').replace('v', ''))
                except: protocol_version = 1
                
            from stage1.atlas import Atlas
            from stage2.crew import ReviewCrew
            
            atlas = Atlas(graph)
            # Hub and Gateway URL simulate local monitor endpoints
            crew = ReviewCrew(
                hub_url="http://localhost:8080/api",
                gateway_url="http://localhost:8080/api",
                team_key="local-test",
                atlas=atlas
            )
            report = crew.run_cycle(cut=cut, protocol_version=protocol_version)
            
            # report is a ReviewReport dataclass, send it as dict
            self.send_json(report.__dict__)
            return
            
        self.send_error(404, f"POST endpoint not found: {path}")

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, file_path: Path):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            mime, _ = mimetypes.guess_type(str(file_path))
            if not mime:
                mime = "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")


def run_server(port: int = 8080, host: str = "0.0.0.0"):
    server_address = (host, port)
    httpd = HTTPServer(server_address, AtlasRequestHandler)
    print(f"==================================================")
    print(f" ATLAS / Study Sentinel Platform")
    print(f" Server running at: http://localhost:{port}")
    print(f" Clinical Monitoring API and UI Ready")
    print(f"==================================================")
    httpd.serve_forever()


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port=port)

import json
import os
import urllib.request
import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Set

from stage1.atlas import Atlas
from starter.schemas import Question
from services.finding_engine import FindingEngine

@dataclass
class ReviewReport:
    cut: int
    protocol_version: int
    total_findings: int
    medical_escalations: int
    queries: int
    compliance_deviations: int
    site_level_escalations: int
    monitor_decisions: List[Dict[str, Any]]
    executed_actions: List[Dict[str, Any]]
    monitoring_only_findings: List[Dict[str, Any]]
    open_queries: int
    trace: List[Dict[str, Any]]

class ReviewCrew:
    def __init__(self, hub_url: str, gateway_url: str, team_key: str, atlas: Atlas):
        self.hub_url = hub_url
        self.gateway_url = gateway_url
        self.team_key = team_key
        self.atlas = atlas
        self.headers = {
            "Authorization": f"Bearer {team_key}",
            "Content-Type": "application/json"
        }
        
        # Persistent memory file
        self.memory_file = "data/crew_memory.json"
        self.query_history: Set[str] = set()
        self.escalation_history: Set[str] = set()
        self.subject_flags: Dict[str, Set[int]] = {}
        self.site_flags: Dict[str, Set[int]] = {}
        self._load_memory()
        
    def _load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    self.query_history = set(data.get("query_history", []))
                    self.escalation_history = set(data.get("escalation_history", []))
                    self.subject_flags = {k: set(v) for k, v in data.get("subject_flags", {}).items()}
                    self.site_flags = {k: set(v) for k, v in data.get("site_flags", {}).items()}
            except Exception:
                pass

    def _save_memory(self):
        os.makedirs("data", exist_ok=True)
        data = {
            "query_history": list(self.query_history),
            "escalation_history": list(self.escalation_history),
            "subject_flags": {k: list(v) for k, v in self.subject_flags.items()},
            "site_flags": {k: list(v) for k, v in self.site_flags.items()}
        }
        with open(self.memory_file, 'w') as f:
            json.dump(data, f, indent=2)
            
    def _post(self, url, payload):
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=self.headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    return type('obj', (object,), {'status_code': 200, 'json': lambda: json.loads(response.read().decode('utf-8'))})()
        except Exception:
            pass
        return type('obj', (object,), {'status_code': 500, 'json': lambda: {}})()
            
    def _add_trace(self, node: str, action: str, trace_list: List[Dict[str, Any]], cut: int, protocol_version: int, evidence: List[str] = None):
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "cut": cut,
            "protocol_version": protocol_version,
            "node": node,
            "action": action,
            "evidence": evidence or []
        }
        trace_list.append(entry)

    def run_cycle(self, cut: int, protocol_version: int) -> ReviewReport:
        trace = []
        engine = FindingEngine()
        
        # ---------------------------------------------------------
        # 1. detect
        # ---------------------------------------------------------
        self.atlas.graph.build(cut=cut)
        all_findings = engine.evaluate_study(self.atlas.graph._internal_graph, cut)
        
        safety_findings = []
        data_findings = []
        compliance_findings = []
        site_findings = []
        
        for f in all_findings:
            c = f.finding_code
            if f.severity == "CRITICAL" or c.startswith("SAE_") or c == "HYS_LAW_CANDIDATE":
                safety_findings.append(f)
            elif c in ["DOSING_ERROR", "SAE_REPORTING_DATE_MISSING"] or "data" in c.lower():
                data_findings.append(f)
            elif "PROHIBITED" in c or "ELIGIBLE" in c or "WINDOW" in c or "RENAL" in c or "COMPLIANCE" in c:
                compliance_findings.append(f)
            elif "SITE" in c:
                site_findings.append(f)
            else:
                if f.severity == "MAJOR":
                    data_findings.append(f)
                else:
                    compliance_findings.append(f)
        
        self._add_trace("detect", f"Detected {len(all_findings)} total findings (safety: {len(safety_findings)}, data: {len(data_findings)}, compliance: {len(compliance_findings)}, site: {len(site_findings)})", trace, cut, protocol_version)
        
        # ---------------------------------------------------------
        # 2. medical_review
        # ---------------------------------------------------------
        escalation_drafts = []
        monitoring_only = []
        
        for f in safety_findings:
            if f.finding_code == "HYS_LAW_CANDIDATE":
                q = Question(id=f"screening_alt_{f.subject}", text=f"What was the ALT at screening for {f.subject}, and is there a concomitant hepatotoxic medication?")
                ans = self.atlas.answer(q)
                ans_text = str(ans.answer).lower() + " " + str(ans.text).lower()
                is_high = ("elevated" in ans_text or "high" in ans_text) and "screening" in ans_text
                
                if is_high:
                    monitoring_only.append({"finding": f.finding_code, "subject": f.subject, "reason": "Screening ALT was already elevated."})
                    self._add_trace("medical_review", f"Liver signal {f.subject} kept monitoring-only (screening ALT already elevated).", trace, cut, protocol_version, f.evidence_references)
                    continue
                else:
                    escalation_drafts.append(f)
                    
            elif f.severity == "CRITICAL" or f.finding_code.startswith("SAE_"):
                escalation_drafts.append(f)
                self._add_trace("medical_review", f"Drafted escalation for {f.finding_code} ({f.subject})", trace, cut, protocol_version, f.evidence_references)
                
        # Subject and Site recurring problems
        for f in all_findings:
            if f.subject:
                if f.subject not in self.subject_flags: self.subject_flags[f.subject] = set()
                self.subject_flags[f.subject].add(cut)
            if f.site:
                if f.site not in self.site_flags: self.site_flags[f.site] = set()
                self.site_flags[f.site].add(cut)
                
        for subj, cuts in self.subject_flags.items():
            if len(cuts) >= 2 and f"RECURRING_SUBJECT|{subj}" not in self.escalation_history:
                from models.finding import Finding
                recur_f = Finding(
                    finding_code="RECURRING_SUBJECT", subject=subj, site="", domain="*",
                    description=f"Subject {subj} flagged in multiple cycles.",
                    protocol_version=str(protocol_version), data_cut=cut, severity="MAJOR", evidence_references=[f"SUBJECT|{subj}|1"]
                )
                escalation_drafts.append(recur_f)
                self._add_trace("medical_review", f"Drafted recurring subject escalation for {subj}", trace, cut, protocol_version, recur_f.evidence_references)
                
        site_level_escalations = 0
        for site, cuts in self.site_flags.items():
            if len(cuts) >= 2 and f"RECURRING_SITE|{site}" not in self.escalation_history:
                from models.finding import Finding
                recur_s = Finding(
                    finding_code="RECURRING_SITE", subject="", site=site, domain="*",
                    description=f"Site {site} has recurring problems across multiple cycles.",
                    protocol_version=str(protocol_version), data_cut=cut, severity="MAJOR", evidence_references=[f"SITE|{site}|1"]
                )
                escalation_drafts.append(recur_s)
                site_level_escalations += 1
                self._add_trace("medical_review", f"Drafted recurring site escalation for {site}", trace, cut, protocol_version, recur_s.evidence_references)
                
        # ---------------------------------------------------------
        # 3. data_manager
        # ---------------------------------------------------------
        new_queries = 0
        
        for f in data_findings:
            if not f.evidence_references: 
                continue
            ev = f.evidence_references[0]
            if ev in self.query_history:
                self._add_trace("data_manager", f"duplicate_prevented: Query already exists for {ev}", trace, cut, protocol_version, [ev])
                continue
                
            self.query_history.add(ev)
            new_queries += 1
            
            parts = ev.split('|')
            if len(parts) >= 3:
                query_payload = {
                    "usubjid": f.subject, "domain": parts[0], "seq": int(parts[2]),
                    "cut": cut, "text": f.description + " Please verify against source and correct or confirm."
                }
                self._add_trace("data_manager", f"Query raised on {ev}: {f.description}", trace, cut, protocol_version, [ev])
                try: self._post(f"{self.gateway_url}/queries", query_payload)
                except Exception: pass
                
        # ---------------------------------------------------------
        # 4. compliance
        # ---------------------------------------------------------
        self._add_trace("compliance", f"{len(compliance_findings)} deviations under v{protocol_version}", trace, cut, protocol_version)
        
        # ---------------------------------------------------------
        # 5. human_gate
        # ---------------------------------------------------------
        valid_escalations = []
        for f in escalation_drafts:
            hk = f"{f.finding_code}|{f.subject}" if f.subject else f"{f.finding_code}|{f.site}"
            if hk not in self.escalation_history:
                valid_escalations.append(f)
            else:
                self._add_trace("human_gate", f"Duplicate escalation prevented for {hk}", trace, cut, protocol_version, f.evidence_references)
                
        monitor_decisions = []
        executed_actions = []
        escalated_count = 0
        
        for f in valid_escalations:
            hk = f"{f.finding_code}|{f.subject}" if f.subject else f"{f.finding_code}|{f.site}"
            
            payload = {
                "code": f.finding_code,
                "usubjid": f.subject,
                "severity": f.severity,
                "summary": f.description,
                "evidence": [],
                "alternatives": ["Accept", "Reject"]
            }
            
            if f.finding_code == "SAE_DISCREPANCY_AESHOSP":
                payload["code"] = "SAE_MISCODED"
                hk = f"SAE_MISCODED|{f.subject}"
                
            for ev in f.evidence_references:
                parts = ev.split('|')
                if len(parts) >= 3:
                    payload["evidence"].append({"domain": parts[0], "usubjid": parts[1], "seq": int(parts[2])})
            
            try:
                resp = self._post(f"{self.gateway_url}/escalations", payload)
                decision = None
                reason = "No response"
                
                if resp.status_code == 200:
                    decision_data = resp.json()
                    decision = decision_data.get("decision")
                    reason = decision_data.get("reason", "")
                
                if decision == "CLARIFY":
                    q = Question(id="clarify", text=reason)
                    ans = self.atlas.answer(q)
                    payload["summary"] += f" Clarification: {ans.answer}. {ans.text}"
                    
                    self._add_trace("human_gate", f"CLARIFY requested for {hk}. Answered from graph: {ans.answer}", trace, cut, protocol_version, f.evidence_references)
                    
                    resp2 = self._post(f"{self.gateway_url}/escalations", payload)
                    if resp2.status_code == 200:
                        decision2_data = resp2.json()
                        decision = decision2_data.get("decision")
                        reason = decision2_data.get("reason", "")
                        
                if decision == "APPROVED":
                    self._add_trace("human_gate", f"APPROVED -> execute: {hk} ({reason})", trace, cut, protocol_version, f.evidence_references)
                    self.escalation_history.add(hk)
                    escalated_count += 1
                    monitor_decisions.append({"id": hk, "decision": decision, "reason": reason})
                    executed_actions.append({"id": hk, "action": payload["summary"]})
                elif decision == "REJECTED":
                    self._add_trace("human_gate", f"REJECTED -> downgraded to monitoring: {hk} ({reason})", trace, cut, protocol_version, f.evidence_references)
                    self.escalation_history.add(hk)
                    monitor_decisions.append({"id": hk, "decision": decision, "reason": reason})
                    monitoring_only.append({"finding": hk, "reason": reason})
                else:
                    self._add_trace("human_gate", f"UNKNOWN decision {decision} for {hk}", trace, cut, protocol_version, f.evidence_references)
            except Exception as e:
                self._add_trace("human_gate", f"ERROR posting {hk}: {e}", trace, cut, protocol_version, f.evidence_references)
                
        # Save state
        self._save_memory()
        
        # ---------------------------------------------------------
        # 6. execute
        # ---------------------------------------------------------
        report = ReviewReport(
            cut=cut,
            protocol_version=protocol_version,
            total_findings=len(all_findings),
            medical_escalations=escalated_count,
            queries=new_queries,
            compliance_deviations=len(compliance_findings),
            site_level_escalations=site_level_escalations,
            monitor_decisions=monitor_decisions,
            executed_actions=executed_actions,
            monitoring_only_findings=monitoring_only,
            open_queries=len(self.query_history),
            trace=trace
        )
        
        self._add_trace("execute", "Cycle complete, report generated.", trace, cut, protocol_version)
        
        # Save latest report to data dir
        os.makedirs("data", exist_ok=True)
        with open("data/cycle_report.json", "w") as f:
            # simple dict conversion for dataclass
            json.dump(report.__dict__, f, indent=2)
            
        with open("data/trace.json", "w") as f:
            json.dump(trace, f, indent=2)
            
        return report

# ATLAS / Study Sentinel — Clinical Trial Monitoring Platform

An intelligent, data-driven clinical trial monitoring and safety surveillance platform designed for clinical research associates (CRAs), data managers, and medical monitors.

---

## 🏛 Architectural Highlights

- **Generic & Data-Driven**: Zero hard-coded subject IDs, site IDs, domain structures, or finding answers. The platform discovers and ingests any study directory placed into `data/`.
- **Core StudyGraph Model**: Models clinical relationships hierarchically:
  $$\text{Study} \longrightarrow \text{Protocol Versions} \longrightarrow \text{Data Cuts} \longrightarrow \text{Sites} \longrightarrow \text{Subjects} \longrightarrow \text{Clinical Domains}$$
- **Exact Evidence Identity**: Every factual clinical finding and record is traceable to:
  $$(domain, \text{USUBJID}, \text{DOMAINSEQ})$$
- **Cut-Aware Data Access**: For any requested cut $N$, only records where $\text{cut\_available} \le N$ are exposed.
- **Historical Non-Destructive Corrections**: Retrospective edits from `corrections.csv` only modify views from $\text{correction\_cut} \ge \text{requested cut}$, preserving historical fidelity.
- **Dynamic Protocol Versioning**: Active protocol versions (e.g., v1, v2, v3) are determined dynamically from `cuts.csv`.
- **Laboratory Safety & Reference Ranges**:
  - Reference range lookups strictly keyed by $\text{LAB} + \text{TEST}$.
  - Supports documented enzymatic conversion: $1\ \mu\text{kat/L} = 60\ \text{U/L}$ for transaminases.
  - Distinguishes numeric values, below detection limit ($<5$), not done (`ND`), and missing without converting to zero.
- **Protocol-Aware Finding Engine**:
  - **SAE Detection**: Protocol seriousness criteria (death, hospitalization, life-threatening, disability, congenital defect) + explicit rule that $\text{AESHOSP} = \text{Y}$ mandates SAE classification even when site marked $\text{AESER} \ne \text{Y}$.
  - **SAE 24-Hour Reporting**: Evaluates whether expedited safety reporting was completed within 24 hours of site awareness.
  - **Dosing Error**: Active Drug 10 mg QD / Placebo 0 mg; flags deviations and missing exposure.
  - **Visit Window Compliance**: Dynamically applies Protocol v1 ($\pm 7$ days) vs Protocol v2/v3 ($\pm 3$ days).
  - **Prohibited Medications**: Prohibits Systemic Glucocorticoids (all protocols) and Sulfonylureas (Protocol v3 amendment).
  - **Screening Eligibility**: Age 18–75, HbA1c 7.0–10.5%, stable metformin $\ge 8$ weeks, hepatic ALT/AST $\le 2\times$ ULN, pregnancy exclusion, and serum Creatinine $\le 1.5$ mg/dL (Protocol v2/v3).
  - **Hy's Law Candidate Detection**: Identifies concurrent $\text{ALT/AST} > 3\times\text{ULN}$ and $\text{TBIL} > 2\times\text{ULN}$ within 14 days without cholestasis ($\text{ALP} \le 2\times\text{ULN}$).
  - **Data Quality Findings**: Identifies missing parent records, site-subject mismatches, duplicate tests, impossible dates, and audit-corrected records.
- **External Response Workflow**: Integrates `site_replies.json` ($\text{DOMAIN}|\text{USUBJID}|\text{SEQ}$ with `_default` fallback) and `monitor_decisions.json` ($\text{CODE}|\text{USUBJID}$ supporting `APPROVED`, `REJECTED`, and `CLARIFY` with inquiry text).
- **Study Documents as Evidence**: Protocol, lab manual, and SAP markdown documents stored safely as read-only reference evidence.

---

## 🚀 Running the Platform

To launch the server:
```bash
python run_server.py 8080
```
Then navigate in your browser to:
```text
http://localhost:8080
```

---

## 📂 Project Structure

```text
altas/
├── data/
│   └── STUDY-042/                # CDISC SDTM clinical domain CSVs, cuts, corrections, documents
│       ├── DM.csv, AE.csv, LB.csv, VS.csv, EX.csv, CM.csv, DS.csv, MH.csv, EG.csv
│       ├── cuts.csv, corrections.csv, reference_ranges.csv
│       ├── site_replies.json, monitor_decisions.json
│       └── protocol_v1.md, protocol_v2.md, protocol_v3.md, lab-manual.md, sap.md
├── models/
│   ├── study_record.py           # DomainRecord, EvidenceIdentity, SpecialLabValue
│   ├── graph_nodes.py            # SubjectNode, SiteNode, StudyNode
│   ├── corrections.py            # FieldCorrection model
│   ├── reference_range.py        # LabReferenceRange model
│   ├── finding.py                # Finding model & severity enums
│   ├── responses.py              # SiteReply and MonitorDecision models
│   └── documents.py              # StudyDocument model
├── services/
│   ├── ingestion_service.py      # Generic study loader
│   ├── cut_manager.py            # Cut filtering and protocol mapper
│   ├── correction_service.py     # Non-destructive historical correction engine
│   ├── lab_service.py            # LAB+TEST range interpreter & unit normalizer
│   ├── response_service.py       # Response & decision mapper
│   ├── patient360_service.py     # Comprehensive Patient 360 generator
│   └── finding_engine.py         # Rule orchestration engine
├── graph/
│   ├── study_graph.py            # Core StudyGraph model and traversals
│   └── graph_statistics.py       # Dynamic metrics calculator
├── rules/
│   ├── base_rule.py              # Abstract clinical rule base class
│   ├── sae_rule.py               # SAE criteria & 24h reporting
│   ├── dosing_rule.py            # Exposure & dose verification
│   ├── visit_window_rule.py      # Protocol-aware visit window evaluator
│   ├── prohibited_meds_rule.py   # Glucocorticoid & Sulfonylurea checks
│   ├── screening_rule.py         # Screening inclusion & exclusion
│   ├── hys_law_rule.py           # Hy's law candidate detector
│   ├── data_quality_rule.py      # Duplicates, date logic, and audit trail
│   ├── unit_normalizer.py        # Unit conversions (1 µkat/L = 60 U/L)
│   └── value_parser.py           # <5, ND, blank, numeric parser
├── evidence/
│   └── evidence_locator.py       # Exact evidence retrieval by (domain, USUBJID, SEQ)
├── api/
│   └── main.py                   # REST API & static file HTTP server
├── web/
│   ├── index.html                # Professional clinical monitoring dashboard
│   └── app.js                    # Interactive SPA logic and SVG graph renderer
└── tests/
    └── test_suite.py             # Automated unit and integration tests
```

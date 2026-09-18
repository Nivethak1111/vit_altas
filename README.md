# ATLAS / Study Sentinel

## How we understood the problem
The challenge is to build a Clinical Finding Engine and Answer Engine capable of reading highly complex, evolving clinical trial data (StudyGraph) and answering precise questions about subject safety, data quality, and protocol adherence. Crucially, the system must be aware of interim data cuts, retro-corrections, and changing protocol versions. It must avoid hallucination at all costs and return precise evidence (`DOMAIN|USUBJID|SEQ`) for every claim, while handling "trap" queries gracefully.

## Architecture
The system consists of three major components:
1. **StudyGraph:** A highly optimized in-memory graph structure that indexes clinical records, documents, and audit trails by Subject, Domain, and Sequence. It handles data filtering up to a given `cut_available`.
2. **Clinical Finding Engine:** A modular rule-based engine that evaluates every subject against protocol constraints (SAEs, Dosing Errors, Hy's Law, Prohibited Meds, Visit Windows) to generate deterministic findings.
3. **Answer Engine:** An NLP-driven query parser that maps natural language questions to deterministic search strategies on the StudyGraph and Finding Engine, returning structured answers with exact evidence.

## Tech stack
- **Backend:** Pure Python 3 (no heavy external ML libraries for core deterministic rules).
- **Web UI:** HTML, Vanilla JavaScript, TailwindCSS (for the Dashboard, Patient 360, and Cut Explorer).
- **Data Ingestion:** Python `csv` module for fast tabular reads.

## Data handling
- Data is loaded once into the `StudyGraph` and indexed.
- The `build(cut)` method handles mid-stage data changes by filtering out any record where `cut_available > cut`.
- Retrospective corrections are applied chronologically; if a correction's cut is $\le$ the active cut, the old value is overridden by the new value.
- Unit conversions (e.g., $\mu$kat/L to U/L) are normalized transparently using `unit_normalizer.py`.

## Documents
- Protocol documents and lab manuals are parsed dynamically.
- The engine supports multiple versions (v1, v2, v3) of the protocol, extracting the effective cut and activating specific rule conditions (e.g., tight vs wide visit windows, newly prohibited medications like Sulfonylureas) based on the `cut_available`.

## When the answer is nothing
- "Trap" queries (e.g., asking for non-existent subjects, or looking for SAEs when none exist) are strictly caught by the Answer Engine.
- If the search strategy yields 0 matching records, the engine explicitly returns a `None` or empty array answer with a text payload of "None found." and zero evidence. Hallucination is actively suppressed.

## What we know is weak
- **Complex NLP Combinations:** Queries with multiple compound conditions (e.g., "How many subjects have SAEs AND dosing errors BUT no prohibited meds?") might over-saturate the basic NLP router.
- **Dynamic Rule Inference:** While protocol versions are handled well, completely novel rules hidden deep in unstructured text require manual mapping to a `BaseClinicalRule` subclass.

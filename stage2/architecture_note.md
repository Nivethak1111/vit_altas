# Review Crew Architecture Note

## Node Responsibilities
The `ReviewCrew` implements six sequential nodes to process a data cut:
1. **detect**: Invokes the `FindingEngine` on the `StudyGraph` up to the specified `cut`. Categorizes all findings into safety, data, compliance, and site buckets.
2. **medical_review**: Evaluates safety findings. E.g., checks `HYS_LAW_CANDIDATE` against the `AnswerEngine` to see if the screening ALT was already elevated. If so, downgrades to monitor-only. Generates escalation drafts. Also checks subject and site histories to escalate recurring problems.
3. **data_manager**: Processes data-quality issues by creating actionable queries. It verifies against the `query_history` memory to prevent duplicate queries on the same evidence record. Posts unique queries to `/queries`.
4. **compliance**: Aggregates deviations (visit windows, prohibited meds, eligibility, renal exclusion) under the current cut's active protocol version.
5. **human_gate**: Filters escalation drafts against the `escalation_history` to prevent re-escalation. Submits unique escalations via POST `/escalations` to the medical monitor and handles the immediate decision.
6. **execute**: Assembles the complete `ReviewReport`, detailing findings, escalations, queries, deviations, and appending the generated trace.

## Memory Design
Memory is persisted in the `ReviewCrew` instance across cycles using sets and dictionaries:
- `query_history` (Set): Stores unique evidence identifiers (`DOMAIN|USUBJID|SEQ`) of raised queries. A query already raised is bypassed in future cycles.
- `escalation_history` (Set): Stores unique combinations of `CODE|USUBJID` (or `CODE|SITE`) that have been approved or rejected. These are never re-escalated.
- `subject_flags` & `site_flags` (Dict): Tracks the specific cuts in which a subject or site had findings. If the set of cuts for a subject or site exceeds 1, a new `RECURRING_SUBJECT` or `RECURRING_SITE` escalation is drafted.

## Human Gate & Monitor Replies
The `human_gate` POSTs an escalation and synchronously processes the response:
- **APPROVED**: The action is logged in the trace as approved, and the escalation key is added to `escalation_history` so it won't be repeated.
- **REJECTED**: The action is logged as downgraded to monitoring. The escalation key is added to `escalation_history`, preventing future re-escalations.
- **CLARIFY**: The human gate queries the `Atlas` `AnswerEngine` with the monitor's clarification reason (e.g., querying screening ALT and conmeds). The answer is appended to the escalation summary, and the escalation is immediately resubmitted in the same cycle. The subsequent APPROVED/REJECTED decision is processed as normal.

## Mid-Stage Event (Protocol Amendment)
Partway through, the study protocol changes, and previously compliant subjects are suddenly in violation on the same data.
**What changed in the code?**
Nothing needed to change in the `ReviewCrew` logic. The `FindingEngine` and `StudyGraph` are inherently cut-aware and protocol-version-aware. When `run_cycle` is called with the new `cut` (where the new protocol takes effect), `StudyGraph.get_protocol_for_cut(cut)` automatically fetches the new rules (e.g., a new prohibited medication or stricter renal exclusion), and the rules are evaluated dynamically.

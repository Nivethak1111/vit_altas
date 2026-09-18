"""
Dynamic StudyGraph Statistics Calculator
Dynamically computes subject counts, site counts, domain record distribution,
records available by cut, protocol version mappings, corrections applied,
and missing-value counts across all clinical domains.
Zero hard-coding!
"""
from typing import Any, Dict, List, Optional
from graph.study_graph import StudyGraph


class GraphStatistics:
    @classmethod
    def calculate(cls, graph: StudyGraph, cut: Optional[int] = None) -> Dict[str, Any]:
        available_cuts = graph.cut_manager.get_available_cuts()
        if not available_cuts:
            available_cuts = [1]

        active_cut = cut if cut is not None else (available_cuts[-1] if available_cuts else 1)
        protocol_version = graph.get_protocol_for_cut(active_cut)

        # Subjects and Sites at this cut
        active_subjects = graph.get_all_subjects(cut=active_cut)
        subject_count = len(active_subjects)

        # Sites
        active_sites = set()
        for s in active_subjects:
            active_sites.add(s.site_id)
        site_count = len(active_sites)

        # Records by domain at active cut
        domain_counts: Dict[str, int] = {}
        total_records = 0
        missing_values_by_domain: Dict[str, int] = {}

        # Progression across all cuts
        records_by_cut: Dict[int, int] = {c: 0 for c in available_cuts}

        for (domain, usubjid, seq), rec in graph._record_index.items():
            # For cut progression
            for c in available_cuts:
                if rec.cut_available <= c:
                    records_by_cut[c] += 1

            # For active cut
            if rec.cut_available <= active_cut:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                total_records += 1

                # Missing values count
                for k, v in rec.current_fields.items():
                    if v is None or str(v).strip() in ("", "NA", "NULL", "NONE"):
                        missing_values_by_domain[domain] = missing_values_by_domain.get(domain, 0) + 1

        # Protocol version by cut
        protocol_by_cut = {c: graph.get_protocol_for_cut(c) for c in available_cuts}

        # Corrections count at this cut
        correction_count = 0
        for (domain, usubjid, seq), corrs in graph.correction_service._corrections.items():
            for c in corrs:
                if c.correction_cut <= active_cut:
                    correction_count += 1

        return {
            "study_id": graph.study_id,
            "active_cut": active_cut,
            "protocol_version": protocol_version,
            "subject_count": subject_count,
            "site_count": site_count,
            "total_records": total_records,
            "domain_record_counts": domain_counts,
            "records_available_by_cut": records_by_cut,
            "protocol_version_by_cut": protocol_by_cut,
            "correction_count": correction_count,
            "missing_value_counts_by_domain": missing_values_by_domain,
            "total_missing_values": sum(missing_values_by_domain.values()),
            "available_cuts": available_cuts,
        }

"""
Correction Service
Handles non-destructive, cut-specific corrections from corrections.csv.
Applies corrections ONLY when requested cut >= correction_cut.
Preserves original record identity and historical values at prior cuts.
"""
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from models.corrections import FieldCorrection
from models.study_record import DomainRecord


class CorrectionService:
    def __init__(self, corrections: Optional[List[FieldCorrection]] = None):
        # Key: (domain.upper(), usubjid, int(seq)) -> list of FieldCorrection
        self._corrections: Dict[Tuple[str, str, int], List[FieldCorrection]] = defaultdict(list)
        if corrections:
            for c in corrections:
                self.add_correction(c)

    def add_correction(self, c: FieldCorrection):
        key = (c.domain.upper().strip(), str(c.usubjid).strip(), int(c.seq))
        self._corrections[key].append(c)

    def get_corrections(
        self, domain: str, usubjid: str, seq: int, cut: Optional[int] = None
    ) -> List[FieldCorrection]:
        key = (domain.upper().strip(), str(usubjid).strip(), int(seq))
        corrs = self._corrections.get(key, [])
        if cut is not None:
            return [c for c in corrs if c.correction_cut <= cut]
        return corrs

    def get_latest_correction(
        self, domain: str, usubjid: str, seq: int, cut: Optional[int] = None
    ) -> Optional[FieldCorrection]:
        corrs = self.get_corrections(domain, usubjid, seq, cut)
        if not corrs:
            return None
        # Sort by correction_cut descending
        return sorted(corrs, key=lambda c: c.correction_cut, reverse=True)[0]

    def apply_corrections_to_record(
        self, record: DomainRecord, requested_cut: Optional[int] = None
    ) -> DomainRecord:
        """
        Returns a new DomainRecord copy with fields adjusted to the requested cut view.
        If requested_cut is None, uses record's existing fields.
        """
        corrs = self.get_corrections(record.domain, record.usubjid, record.seq, requested_cut)

        # Clone current fields from original
        fields = dict(record.original_fields)
        history = []
        is_corrected = False
        latest_correction_cut = None

        for c in sorted(corrs, key=lambda x: x.correction_cut):
            fields[c.field_name] = c.corrected_value
            is_corrected = True
            latest_correction_cut = c.correction_cut
            history.append(c.to_dict())

        return DomainRecord(
            domain=record.domain,
            usubjid=record.usubjid,
            seq=record.seq,
            cut_available=record.cut_available,
            corrected_at_cut=latest_correction_cut,
            original_fields=dict(record.original_fields),
            current_fields=fields,
            is_corrected=is_corrected,
            correction_history=history,
        )

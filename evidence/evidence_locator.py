"""
Evidence Locator Service
Resolves exact clinical evidence identities: (domain, USUBJID, SEQ)
and formats them for clinical monitoring audit trails.
"""
from typing import Any, Dict, List, Optional
from models.study_record import DomainRecord, EvidenceIdentity
from utils.errors import RecordNotFoundError


class EvidenceLocator:
    @staticmethod
    def parse_identity(key_or_str: str) -> EvidenceIdentity:
        """
        Parses 'DOMAIN|USUBJID|SEQ' or '(DOMAIN, USUBJID, SEQ)' into EvidenceIdentity.
        """
        clean = key_or_str.strip().strip("()").replace(",", "|")
        parts = [p.strip() for p in clean.split("|") if p.strip()]
        if len(parts) != 3:
            raise ValueError(f"Invalid evidence identity format: {key_or_str}")
        return EvidenceIdentity(domain=parts[0].upper(), usubjid=parts[1], seq=int(parts[2]))

    @classmethod
    def locate_evidence(
        cls, graph: Any, identity_key: str, cut: Optional[int] = None
    ) -> Optional[DomainRecord]:
        try:
            ident = cls.parse_identity(identity_key)
            return graph.get_record(ident.domain, ident.usubjid, ident.seq, cut)
        except (ValueError, RecordNotFoundError):
            return None

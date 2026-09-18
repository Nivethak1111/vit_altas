"""
Generic Data Ingestion Layer
Dynamically discovers and loads CDISC SDTM domain CSVs, cuts, corrections,
reference ranges, external replies/decisions, and protocol/evidence markdown docs.
Does NOT hard-code any study ID, subject ID, site ID, or record count!
"""
import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from models.corrections import FieldCorrection
from models.documents import StudyDocument
from models.reference_range import LabReferenceRange
from models.study_record import DomainRecord
from services.cut_manager import CutMetadata
from utils.errors import StudyNotFoundError


class IngestionService:
    KNOWN_DOMAINS = ["DM", "AE", "LB", "VS", "EX", "CM", "DS", "MH", "EG"]

    @classmethod
    def find_studies(cls, base_data_dir: str) -> List[str]:
        """Discovers all study directory names inside base_data_dir."""
        p = Path(base_data_dir)
        if not p.exists() or not p.is_dir():
            return []
        studies = []
        for item in p.iterdir():
            if item.is_dir():
                # Check if it has any csv or json file
                csvs = list(item.glob("*.csv"))
                if csvs:
                    studies.append(item.name)
        return sorted(studies)

    @classmethod
    def load_study_data(cls, study_dir: str) -> Dict[str, Any]:
        """
        Loads all clinical domain CSVs, reference ranges, corrections, cuts,
        external replies, decisions, and markdown evidence from a study directory.
        """
        p = Path(study_dir)
        if not p.exists() or not p.is_dir():
            raise StudyNotFoundError(f"Study directory not found: {study_dir}")

        study_id = p.name

        # 1. Load cuts.csv
        cuts = cls._load_cuts(p / "cuts.csv")

        # 2. Load corrections.csv
        corrections = cls._load_corrections(p / "corrections.csv")

        # 3. Load reference_ranges.csv
        ranges = cls._load_reference_ranges(p / "reference_ranges.csv")

        # 4. Load site_replies.json & monitor_decisions.json
        site_replies = cls._load_json(p / "site_replies.json")
        monitor_decisions = cls._load_json(p / "monitor_decisions.json")

        # 5. Load markdown evidence documents
        documents = cls._load_documents(p)

        # 6. Load clinical domain CSV files
        records_by_domain: Dict[str, List[DomainRecord]] = {}
        for csv_file in p.glob("*.csv"):
            fname = csv_file.stem.upper()
            if fname in ("CUTS", "CORRECTIONS", "REFERENCE_RANGES"):
                continue
            domain_name = fname
            records = cls._load_domain_csv(csv_file, domain_name)
            records_by_domain[domain_name] = records

        return {
            "study_id": study_id,
            "cuts": cuts,
            "corrections": corrections,
            "reference_ranges": ranges,
            "site_replies": site_replies,
            "monitor_decisions": monitor_decisions,
            "documents": documents,
            "records_by_domain": records_by_domain,
        }

    @classmethod
    def _load_csv_rows(cls, filepath: Path) -> List[Dict[str, str]]:
        if not filepath.exists():
            return []
        rows = []
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                # Strip keys and values
                clean_row = {
                    k.strip() if k else "": v.strip() if v else ""
                    for k, v in r.items()
                    if k is not None
                }
                rows.append(clean_row)
        return rows

    @classmethod
    def _load_cuts(cls, filepath: Path) -> List[CutMetadata]:
        rows = cls._load_csv_rows(filepath)
        cuts = []
        for r in rows:
            cut_id_raw = r.get("cut_id") or r.get("cut") or r.get("CUT_ID") or r.get("CUT") or "1"
            try:
                cut_id = int(cut_id_raw)
            except ValueError:
                cut_id = 1
            cut_date = r.get("cut_date") or r.get("date") or r.get("CUT_DATE") or ""
            protocol = r.get("protocol_version") or r.get("protocol") or r.get("PROTOCOL") or "v1"
            desc = r.get("description") or r.get("desc") or ""
            cuts.append(CutMetadata(cut_id=cut_id, cut_date=cut_date, protocol_version=protocol, description=desc))
        if not cuts:
            # Default minimum cut 1
            cuts.append(CutMetadata(cut_id=1, cut_date="2024-01-01", protocol_version="v1", description="Initial Cut"))
        return sorted(cuts, key=lambda c: c.cut_id)

    @classmethod
    def _load_corrections(cls, filepath: Path) -> List[FieldCorrection]:
        rows = cls._load_csv_rows(filepath)
        corrections = []
        for r in rows:
            domain = r.get("domain") or r.get("DOMAIN") or ""
            usubjid = r.get("usubjid") or r.get("USUBJID") or ""
            seq_raw = r.get("seq") or r.get("SEQ") or r.get(f"{domain}SEQ") or "1"
            try:
                seq = int(seq_raw)
            except ValueError:
                seq = 1
            field_name = r.get("field_name") or r.get("variable") or r.get("field") or r.get("FIELD") or ""
            orig = r.get("original_value") or r.get("orig_value") or r.get("ORIGINAL_VALUE") or ""
            corr = r.get("corrected_value") or r.get("corr_value") or r.get("CORRECTED_VALUE") or ""
            cut_raw = r.get("correction_cut") or r.get("cut") or r.get("CORRECTION_CUT") or "1"
            try:
                c_cut = int(cut_raw)
            except ValueError:
                c_cut = 1
            reason = r.get("reason") or r.get("REASON") or ""

            corrections.append(
                FieldCorrection(
                    domain=domain,
                    usubjid=usubjid,
                    seq=seq,
                    field_name=field_name,
                    original_value=orig,
                    corrected_value=corr,
                    correction_cut=c_cut,
                    reason=reason,
                )
            )
        return corrections

    @classmethod
    def _load_reference_ranges(cls, filepath: Path) -> List[LabReferenceRange]:
        rows = cls._load_csv_rows(filepath)
        ranges = []
        for r in rows:
            lab = r.get("lab") or r.get("LAB") or r.get("laboratory") or r.get("LBNAM") or "CENTRAL LAB"
            test = r.get("test") or r.get("TEST") or r.get("LBTEST") or r.get("LBTESTCD") or ""
            unit = r.get("unit") or r.get("UNIT") or r.get("LBORRESU") or ""
            low_raw = r.get("low") or r.get("LOW") or r.get("lower_limit") or r.get("LBNRLO") or ""
            high_raw = r.get("high") or r.get("HIGH") or r.get("upper_limit") or r.get("LBNRHI") or ""
            sex = r.get("sex") or r.get("SEX") or None

            low = None
            if low_raw and low_raw.upper() not in ("NA", "NULL", ""):
                try:
                    low = float(low_raw)
                except ValueError:
                    low = None

            high = None
            if high_raw and high_raw.upper() not in ("NA", "NULL", ""):
                try:
                    high = float(high_raw)
                except ValueError:
                    high = None

            ranges.append(LabReferenceRange(lab=lab, test=test, unit=unit, low=low, high=high, sex=sex))
        return ranges

    @classmethod
    def _load_json(cls, filepath: Path) -> Dict[str, Any]:
        if not filepath.exists():
            return {}
        try:
            with open(filepath, mode="r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def _load_documents(cls, study_dir: Path) -> List[StudyDocument]:
        docs = []
        for md_file in study_dir.glob("*.md"):
            name = md_file.name
            stem = md_file.stem.lower()
            doc_type = "document"
            version = "1.0"

            if "protocol" in stem:
                doc_type = "protocol"
                if "v3" in stem or "_3" in stem:
                    version = "v3"
                elif "v2" in stem or "_2" in stem:
                    version = "v2"
                else:
                    version = "v1"
            elif "lab" in stem or "manual" in stem:
                doc_type = "lab_manual"
                if "v3" in stem:
                    version = "v3"
                else:
                    version = "v1"
            elif "sap" in stem:
                doc_type = "sap"
                version = "v1"

            try:
                with open(md_file, mode="r", encoding="utf-8") as f:
                    content = f.read()
                docs.append(StudyDocument(name=name, doc_type=doc_type, version=version, content=content))
            except Exception:
                continue
        return docs

    @classmethod
    def _load_domain_csv(cls, filepath: Path, domain: str) -> List[DomainRecord]:
        rows = cls._load_csv_rows(filepath)
        records = []
        seq_col = f"{domain}SEQ".upper()
        subject_seq_counter: Dict[str, int] = {}

        for idx, r in enumerate(rows, start=1):
            usubjid = r.get("USUBJID") or r.get("usubjid") or r.get("SUBJID") or r.get("subjid") or ""
            subject_seq_counter[usubjid] = subject_seq_counter.get(usubjid, 0) + 1

            # Domain sequence number: check domainSEQ, SEQ, seq, or per-subject counter
            seq_val = r.get(seq_col) or r.get("SEQ") or r.get("seq")
            if seq_val:
                try:
                    seq = int(seq_val)
                except ValueError:
                    seq = subject_seq_counter[usubjid]
            else:
                seq = subject_seq_counter[usubjid]

            # Cut availability (defaults to 1 if not specified)
            cut_avail_val = r.get("cut_available") or r.get("CUT_AVAILABLE") or r.get("cut") or "1"
            try:
                cut_available = int(cut_avail_val)
            except ValueError:
                cut_available = 1

            rec = DomainRecord(
                domain=domain,
                usubjid=usubjid,
                seq=seq,
                cut_available=cut_available,
                original_fields=dict(r),
                current_fields=dict(r),
            )
            records.append(rec)
        return records

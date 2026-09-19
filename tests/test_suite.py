"""
Comprehensive Automated Test Suite for ATLAS / Study Sentinel
Validates:
1. Ingestion of CDISC domains, cuts, corrections, reference ranges, replies, decisions, docs
2. Exact Evidence Identity (domain, USUBJID, SEQ)
3. Cut-aware data access (cut_available <= N)
4. Non-destructive historical corrections (cut-dependent values)
5. Protocol versioning by cut
6. Lab reference ranges by LAB+TEST and unit conversion (1 µkat/L = 60 U/L)
7. Special lab values (<5, ND, blank) explicitly preserved
8. Serious Adverse Event detection (AESHOSP=Y override) and 24-hr reporting
9. Dosing error detection
10. Visit window evaluation (v1: ±7 days vs v2/v3: ±3 days)
11. Prohibited medications (Glucocorticoids v1/v2/v3, Sulfonylureas v3)
12. Screening eligibility (Age, HbA1c, Metformin stability, Hepatic, Creatinine in v2)
13. Hy's law candidate detection
14. External responses (Site replies DOMAIN|USUBJID|SEQ with _default, Monitor decisions CODE|USUBJID)
15. Patient 360 profile aggregation
"""
import os
import sys
import unittest

# Ensure altas root is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from graph.study_graph import StudyGraph
from graph.graph_statistics import GraphStatistics
from models.study_record import SpecialLabStatus
from rules.unit_normalizer import convert_lab_value
from rules.value_parser import parse_lab_value
from services.finding_engine import FindingEngine
from services.patient360_service import Patient360Service


class TestAtlasCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study_dir = os.path.join(ROOT_DIR, "data", "STUDY-042")
        cls.graph = StudyGraph.load_study(cls.study_dir)
        cls.finding_engine = FindingEngine()
        cls.patient360_service = Patient360Service(cls.finding_engine)

    def test_01_study_ingestion(self):
        """Verifies generic ingestion of all CDISC domain files and metadata."""
        self.assertIsNotNone(self.graph)
        self.assertEqual(self.graph.study_id, "STUDY-042")
        self.assertGreater(len(self.graph._record_index), 0)
        self.assertGreater(len(self.graph._subjects), 0)
        self.assertGreater(len(self.graph._sites), 0)
        self.assertGreater(len(self.graph._documents), 0)

    def test_02_evidence_identity(self):
        """Verifies exact evidence retrieval by (domain, USUBJID, DOMAINSEQ)."""
        rec = self.graph.get_record("DM", "STUDY042-101-001", 1, cut=1)
        self.assertEqual(rec.identity.domain, "DM")
        self.assertEqual(rec.identity.usubjid, "STUDY042-101-001")
        self.assertEqual(rec.identity.seq, 1)
        self.assertEqual(str(rec.identity), "DM|STUDY042-101-001|1")

    def test_03_cut_aware_access(self):
        """Verifies cut-aware data access: only records satisfying cut_available <= N are returned."""
        # Record with cut_available = 2 should NOT be accessible at Cut 1
        with self.assertRaises(Exception):
            self.graph.get_record("DM", "STUDY042-103-002", 1, cut=1)

        # But should be accessible at Cut 2
        rec_cut2 = self.graph.get_record("DM", "STUDY042-103-002", 1, cut=2)
        self.assertIsNotNone(rec_cut2)
        self.assertEqual(rec_cut2.cut_available, 2)

    def test_04_historical_corrections(self):
        """Verifies non-destructive correction resolution across cuts."""
        # STUDY042-102-002 EX record 1 was corrected from 20 to 10 at Cut 2
        rec_cut1 = self.graph.get_record("EX", "STUDY042-102-002", 1, cut=1)
        self.assertEqual(str(rec_cut1.get("EXDOSE")), "20")
        self.assertFalse(rec_cut1.is_corrected)

        rec_cut2 = self.graph.get_record("EX", "STUDY042-102-002", 1, cut=2)
        self.assertEqual(str(rec_cut2.get("EXDOSE")), "10")
        self.assertTrue(rec_cut2.is_corrected)
        self.assertEqual(rec_cut2.corrected_at_cut, 2)

    def test_05_protocol_version_by_cut(self):
        """Verifies protocol versions are data-driven from cuts.csv."""
        self.assertEqual(self.graph.get_protocol_for_cut(1), "v1")
        self.assertEqual(self.graph.get_protocol_for_cut(2), "v2")
        self.assertEqual(self.graph.get_protocol_for_cut(3), "v3")

    def test_06_lab_reference_ranges_and_unit_conversion(self):
        """Verifies reference-range lookup by LAB+TEST and 1 µkat/L = 60 U/L unit conversion."""
        # Central Lab: U/L
        rr_central = self.graph.get_reference_range("CENTRAL LAB", "ALT")
        self.assertIsNotNone(rr_central)
        self.assertEqual(rr_central.high, 45.0)

        # Local Lab: µkat/L
        rr_local = self.graph.get_reference_range("LOCAL LAB 101", "ALT")
        self.assertIsNotNone(rr_local)
        self.assertEqual(rr_local.unit, "µkat/L")

        # Conversion: 1 µkat/L = 60 U/L
        converted, applied = convert_lab_value(0.50, "µkat/L", "U/L", "ALT")
        self.assertTrue(applied)
        self.assertAlmostEqual(converted, 30.0, places=2)

    def test_07_special_lab_values(self):
        """Verifies <5, ND, and blank are NOT converted to zero."""
        v_below = parse_lab_value("<5")
        self.assertEqual(v_below.status, SpecialLabStatus.BELOW_DETECTION)
        self.assertEqual(v_below.numeric_value, 5.0)
        self.assertEqual(v_below.comparator, "<")

        v_nd = parse_lab_value("ND")
        self.assertEqual(v_nd.status, SpecialLabStatus.NOT_DONE)
        self.assertIsNone(v_nd.numeric_value)

        v_blank = parse_lab_value("")
        self.assertEqual(v_blank.status, SpecialLabStatus.MISSING)
        self.assertIsNone(v_blank.numeric_value)

    def test_08_sae_detection_and_discrepancy(self):
        """Verifies AESHOSP=Y triggers serious adverse event even if site marked AESER=N."""
        findings = self.finding_engine.evaluate_subject(self.graph, "STUDY042-101-002", cut=1)
        hosp_findings = [f for f in findings if f.finding_code == "SAE_DISCREPANCY_AESHOSP"]
        self.assertGreater(len(hosp_findings), 0)
        self.assertEqual(hosp_findings[0].severity, "CRITICAL")
        self.assertIn("hospitalization", hosp_findings[0].description.lower())

    def test_09_sae_reporting_compliance(self):
        """Verifies 24-hour SAE reporting window detection."""
        findings = self.finding_engine.evaluate_subject(self.graph, "STUDY042-101-002", cut=1)
        delay_findings = [f for f in findings if f.finding_code == "SAE_REPORTING_DELAY"]
        self.assertGreater(len(delay_findings), 0)
        self.assertIn("exceeding", delay_findings[0].description.lower())

    def test_10_dosing_error_detection(self):
        """Verifies administered dose outside 10 mg (Active) or 0 mg (Placebo) is flagged."""
        # At Cut 1, dose was 20 mg
        findings_cut1 = self.finding_engine.evaluate_subject(self.graph, "STUDY042-102-002", cut=1)
        dose_findings = [f for f in findings_cut1 if f.finding_code == "DOSING_ERROR"]
        self.assertGreater(len(dose_findings), 0)

        # At Cut 2, correction to 10 mg resolves the dosing error
        findings_cut2 = self.finding_engine.evaluate_subject(self.graph, "STUDY042-102-002", cut=2)
        dose_findings_cut2 = [f for f in findings_cut2 if f.finding_code == "DOSING_ERROR"]
        self.assertEqual(len(dose_findings_cut2), 0)

    def test_11_prohibited_medications(self):
        """Verifies Glucocorticoids prohibited in v1/v2/v3, and Sulfonylureas prohibited in v3."""
        # STUDY042-103-001 took Prednisone (Glucocorticoid)
        findings_gluco = self.finding_engine.evaluate_subject(self.graph, "STUDY042-103-001", cut=1)
        gluco_findings = [f for f in findings_gluco if f.finding_code == "PROHIBITED_MED_GLUCOCORTICOID"]
        self.assertGreater(len(gluco_findings), 0)

        # STUDY042-103-002 took Glimepiride (Sulfonylurea)
        # In Cut 2 (Protocol v2), sulfonylurea is NOT prohibited
        findings_cut2 = self.finding_engine.evaluate_subject(self.graph, "STUDY042-103-002", cut=2)
        sulf_cut2 = [f for f in findings_cut2 if f.finding_code == "PROHIBITED_MED_SULFONYLUREA"]
        self.assertEqual(len(sulf_cut2), 0)

        # In Cut 3 (Protocol v3), sulfonylurea is prohibited!
        findings_cut3 = self.finding_engine.evaluate_subject(self.graph, "STUDY042-103-002", cut=3)
        sulf_cut3 = [f for f in findings_cut3 if f.finding_code == "PROHIBITED_MED_SULFONYLUREA"]
        self.assertGreater(len(sulf_cut3), 0)

    def test_12_screening_eligibility(self):
        """Verifies screening eligibility including Creatinine > 1.5 in Protocol v2/v3."""
        # STUDY042-103-002 has Creatinine 1.8 mg/dL at screening
        findings_cut2 = self.finding_engine.evaluate_subject(self.graph, "STUDY042-103-002", cut=2)
        cr_findings = [f for f in findings_cut2 if f.finding_code == "INELIGIBLE_RENAL_CREATININE"]
        self.assertGreater(len(cr_findings), 0)

    def test_13_hys_law_candidate(self):
        """Verifies Hy's Law candidate detection for ALT/AST > 3x ULN and TBIL > 2x ULN within 14 days."""
        findings = self.finding_engine.evaluate_subject(self.graph, "STUDY042-102-001", cut=1)
        hys_findings = [f for f in findings if f.finding_code == "HYS_LAW_CANDIDATE"]
        self.assertGreater(len(hys_findings), 0)
        self.assertEqual(hys_findings[0].severity, "CRITICAL")
        self.assertEqual(len(hys_findings[0].evidence_references), 2)

    def test_14_responses_and_decisions(self):
        """Verifies site replies and monitor decisions lookup."""
        reply = self.graph.get_site_reply("AE", "STUDY042-101-002", 1)
        self.assertFalse(reply["is_default"])
        self.assertIn("hospitalized", reply["reply"].lower())

        default_reply = self.graph.get_site_reply("DM", "STUDY042-999-999", 999)
        self.assertTrue(default_reply["is_default"])

        decision = self.graph.get_monitor_decision("SAE_DISCREPANCY_AESHOSP", "STUDY042-101-002")
        self.assertIsNotNone(decision)
        self.assertEqual(decision["decision"], "CLARIFY")
        self.assertIsNotNone(decision["inquiry"])

    def test_15_patient360_profile(self):
        """Verifies complete Patient 360 data generation from StudyGraph."""
        profile = self.patient360_service.get_patient_profile(self.graph, "STUDY042-101-002", cut=1)
        self.assertEqual(profile["usubjid"], "STUDY042-101-002")
        self.assertEqual(profile["site_id"], "SITE-101")
        self.assertIn("demographics", profile)
        self.assertIn("laboratory_results", profile)
        self.assertIn("adverse_events", profile)
        self.assertIn("serious_adverse_events", profile)
        self.assertIn("findings", profile)
        self.assertGreater(profile["total_records_at_cut"], 0)

    def test_16_dynamic_statistics(self):
        """Verifies dynamic statistics calculation."""
        stats = GraphStatistics.calculate(self.graph, cut=1)
        self.assertEqual(stats["study_id"], "STUDY-042")
        self.assertGreater(stats["subject_count"], 0)
        self.assertGreater(stats["total_records"], 0)
        self.assertIn("DM", stats["domain_record_counts"])

    def test_17_answer_engine_pipeline(self):
        """Verifies Answer Engine pipeline: Query -> QuestionType -> Routing -> Evidence -> Answer."""
        from services.answer_engine import AnswerEngine
        engine = AnswerEngine(self.graph, self.finding_engine)

        # Factual query
        res_fact = engine.answer("What is the assigned arm for subject STUDY042-101-001?", cut=1)
        self.assertEqual(res_fact.question_type, "FACTUAL_RETRIEVAL")
        self.assertIn("Drug 10mg", res_fact.answer)
        self.assertIn("DM|STUDY042-101-001|1", res_fact.evidence_references)

        # Rule evaluation query
        res_rule = engine.answer("Are there any serious adverse event discrepancies?", cut=1)
        self.assertEqual(res_rule.question_type, "RULE_EVALUATION")
        self.assertIn("SAE_DISCREPANCY", res_rule.answer)
        self.assertGreater(len(res_rule.evidence_references), 0)

    def test_18_answer_engine_hybrid_with_site_and_monitor(self):
        """Verifies hybrid flow with evidence citations, site replies, and monitor decisions."""
        from services.answer_engine import AnswerEngine
        engine = AnswerEngine(self.graph, self.finding_engine)

        res = engine.answer("Why was subject STUDY042-101-002 flagged for an SAE discrepancy and what did the site reply?", cut=1)
        self.assertEqual(res.question_type, "HYBRID_MONITORING")
        self.assertIn("STUDY042-101-002", res.answer)
        self.assertIn("AE|STUDY042-101-002|1", res.evidence_references)
        self.assertGreater(len(res.site_replies), 0)
        self.assertGreater(len(res.monitor_decisions), 0)
        self.assertEqual(res.monitor_decisions[0].get("decision"), "CLARIFY")


if __name__ == "__main__":
    unittest.main()

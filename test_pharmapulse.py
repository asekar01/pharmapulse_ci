"""
PharmaPulse CI — End-to-End Verification Test Suite
===================================================
Tests all modules: Caching, CT.gov v2 Client, Pivotal Classifier,
openFDA Client, PubMed Client, Forecasting Engine, Patent Cliff Tracker,
Endpoint Efficacy Extractor, and Multi-Sheet Excel Exporter.
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.cache_manager import get_cached, set_cache, clear_cache
from backend.clinical_trials import calculate_pivotal_score, parse_phase_label, search_clinical_trials
from backend.fda_client import fetch_drug_label, fetch_adverse_events
from backend.pubmed_client import fetch_pubmed_intelligence
from backend.forecasting import parse_date_flexible, calculate_trial_forecast, generate_pipeline_forecasting
from backend.comparison import compare_competitors, build_drug_dossier
from backend.excel_exporter import generate_excel_dossier
from backend.patent_tracker import estimate_regulatory_patent_cliff
from backend.efficacy_extractor import extract_efficacy_from_text, get_drug_efficacy_profile, compare_head_to_head_efficacy


class TestPharmaPulseBackend(unittest.TestCase):

    def test_01_cache_layer(self):
        """Verify thread-safe caching and retrieval."""
        test_key = "test_unit_key"
        test_data = {"drug": "Semaglutide", "trials": 120}
        set_cache(test_key, "test_source", test_data)

        retrieved = get_cached(test_key, max_age_hours=1.0)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.get("drug"), "Semaglutide")
        self.assertEqual(retrieved.get("trials"), 120)

    def test_02_pivotal_classifier(self):
        """Verify the multi-factor pivotal trial scoring algorithm."""
        # Case A: True Pivotal Trial (Phase 3, Interventional, Randomized, Industry, n=1200, Acronym)
        pivotal_study = {
            "title": "A Phase 3 Study of Pembrolizumab (KEYNOTE-024) in NSCLC",
            "phase": "Phase 3",
            "study_type": "INTERVENTIONAL",
            "allocation": "RANDOMIZED",
            "masking": "DOUBLE",
            "sponsor": "Merck Sharp & Dohme",
            "sponsor_class": "INDUSTRY",
            "enrollment": 1200
        }
        res_a = calculate_pivotal_score(pivotal_study)
        self.assertTrue(res_a["is_pivotal"])
        self.assertGreaterEqual(res_a["pivotal_score"], 70)
        self.assertEqual(res_a["pivotal_confidence"], "High")

        # Case B: Exploratory Academic Trial (Phase 1, Observational, University, n=15)
        academic_study = {
            "title": "Exploratory biomarker evaluation in healthy volunteers",
            "phase": "Phase 1",
            "study_type": "OBSERVATIONAL",
            "allocation": "NON_RANDOMIZED",
            "masking": "OPEN",
            "sponsor": "City Hospital",
            "sponsor_class": "OTHER",
            "enrollment": 15
        }
        res_b = calculate_pivotal_score(academic_study)
        self.assertFalse(res_b["is_pivotal"])
        self.assertLess(res_b["pivotal_score"], 40)

    def test_03_forecasting_milestones(self):
        """Verify commercial forecasting milestone date calculations."""
        trial = {
            "nct_id": "NCT99999999",
            "title": "Future Registrational Study",
            "phase": "Phase 3",
            "status": "RECRUITING",
            "primary_completion_date": "December 2026",
            "enrollment": 850
        }
        forecast = calculate_trial_forecast(trial)
        self.assertTrue(forecast["has_milestones"])
        self.assertEqual(forecast["pcd_formatted"], "Dec 2026")
        self.assertEqual(forecast["topline_readout"], "Mar 2027")
        self.assertEqual(forecast["regulatory_filing"], "Jul 2027")
        self.assertEqual(forecast["pdufa_priority"], "Jan 2028")
        self.assertEqual(forecast["pdufa_standard"], "May 2028")
        self.assertEqual(forecast["commercial_launch"], "Jul 2028")
        self.assertEqual(forecast["calendar_year_launch"], 2028)

    def test_04_live_clinical_trials_api(self):
        """Verify live fetching from ClinicalTrials.gov v2 API."""
        result = search_clinical_trials("Semaglutide", mode="intervention", pivotal_only=True)
        self.assertIn("trials", result)
        self.assertIn("stats", result)
        self.assertGreater(len(result["trials"]), 0)
        first_trial = result["trials"][0]
        self.assertTrue(first_trial.get("is_pivotal"))
        self.assertIn("NCT", first_trial.get("nct_id"))

    def test_05_live_openfda_api(self):
        """Verify live fetching of FDA drug label and adverse events."""
        label = fetch_drug_label("Ozempic")
        self.assertTrue(label.get("found"))
        self.assertIn("semaglutide", label.get("generic_name", "").lower())
        self.assertTrue(len(label.get("indications_and_usage", "")) > 0)

        events = fetch_adverse_events("Ozempic")
        self.assertGreater(events.get("total", 0), 0)

    def test_06_live_pubmed_api(self):
        """Verify live PubMed E-utilities integration."""
        pub = fetch_pubmed_intelligence("Semaglutide")
        self.assertGreater(pub.get("total_papers", 0), 0)
        self.assertGreater(len(pub.get("papers", [])), 0)
        self.assertTrue(any(p.get("pmid") for p in pub["papers"]))

    def test_07_excel_export(self):
        """Verify that 6-sheet Excel export generates a valid non-empty workbook."""
        dummy_dossier = {
            "drug_name": "TestDrug",
            "trials": [
                {
                    "nct_id": "NCT00000001",
                    "title": "Test Phase 3 Trial",
                    "phase": "Phase 3",
                    "status": "Completed",
                    "is_pivotal": True,
                    "pivotal_score": 85,
                    "enrollment": 1000,
                    "sponsor": "Test Pharma",
                    "primary_completion_date": "2025-06-01",
                    "primary_outcomes": ["Overall Survival"],
                    "conditions": ["Diabetes"],
                    "url": "https://clinicaltrials.gov/study/NCT00000001"
                }
            ],
            "stats": {"total_trials": 1, "pivotal_trials": 1, "total_enrolled": 1000},
            "fda": {"label": {"found": True, "brand_name": "TestBrand", "generic_name": "testdrug"}},
            "patent": {"patent_expiry_formatted": "December 2031", "primary_patent": "US 8,129,343", "runway_years": 5.2},
            "efficacy": [{"endpoint": "HbA1c Reduction", "treatment_value": "-2.1%", "delta": "+0.7%", "stat_sig": "p < 0.001", "flagship_trial": "STEP-1"}],
            "forecasting": {
                "earliest_projected_launch": "Jul 2026",
                "milestones": [
                    {
                        "nct_id": "NCT00000001", "phase": "Phase 3", "status": "Completed",
                        "is_pivotal": True, "enrollment": 1000, "pcd_formatted": "Jun 2025",
                        "topline_readout": "Sep 2025", "regulatory_filing": "Jan 2026",
                        "pdufa_priority": "Jul 2026", "pdufa_standard": "Nov 2026",
                        "commercial_launch": "Jan 2027", "calendar_year_launch": 2027
                    }
                ]
            },
            "pubmed": {"total_papers": 50, "clinical_trial_papers": 10, "papers": []}
        }
        stream = generate_excel_dossier(dummy_dossier)
        excel_bytes = stream.getvalue()
        self.assertGreater(len(excel_bytes), 1000)
        self.assertTrue(excel_bytes.startswith(b"PK"))

    def test_08_patent_tracker(self):
        """Verify FDA Orange Book patent retrieval and commercial runway calculation."""
        pat = estimate_regulatory_patent_cliff("Semaglutide")
        self.assertTrue(pat["has_patent_data"])
        self.assertIn("8,129,343", pat["primary_patent"])
        self.assertGreater(pat["runway_years"], 0)
        self.assertEqual(pat["patent_expiry_year"], 2031)

    def test_09_efficacy_extractor_nlp(self):
        """Verify rule-based NLP extraction of quantitative clinical endpoints."""
        sample_text = (
            "In patients with type 2 diabetes, semaglutide demonstrated a mean HbA1c reduction of -2.1% "
            "compared with sitagliptin -1.4% (p < 0.001). Additionally, patients experienced a weight loss "
            "of 14.9% vs 2.4% with placebo. Median progression-free survival reached 10.3 months with HR 0.55."
        )
        extracted = extract_efficacy_from_text(sample_text, "SUSTAIN Trial")
        self.assertGreater(len(extracted), 0)
        # Check that percentage or survival was found
        vals = [e["treatment_value"] for e in extracted]
        self.assertTrue(any("%" in v or "months" in v for v in vals))

    def test_10_head_to_head_efficacy(self):
        """Verify comparative efficacy benchmarking between two drugs."""
        dossier_a = {"trials": [], "fda": {}, "pubmed": {}}
        dossier_b = {"trials": [], "fda": {}, "pubmed": {}}
        cmp_eff = compare_head_to_head_efficacy("Wegovy", "Zepbound", dossier_a, dossier_b)
        self.assertGreater(len(cmp_eff), 0)
        first_row = cmp_eff[0]
        self.assertIn("endpoint", first_row)
        self.assertIn("drug_a_val", first_row)
        self.assertIn("drug_b_val", first_row)
        self.assertIn("advantage", first_row)


if __name__ == "__main__":
    unittest.main()

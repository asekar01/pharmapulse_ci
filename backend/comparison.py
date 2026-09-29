"""
PharmaPulse CI — Head-to-Head Competitor Comparison Engine
==========================================================
Executes concurrent queries for Drug A vs Drug B and builds a
structured side-by-side competitive intelligence matrix including
patent cliff runways and clinical endpoint efficacy benchmarks.
"""

from typing import Dict, Any, List
import concurrent.futures
from .clinical_trials import search_clinical_trials
from .fda_client import get_full_regulatory_dossier
from .pubmed_client import fetch_pubmed_intelligence
from .forecasting import generate_pipeline_forecasting
from .patent_tracker import estimate_regulatory_patent_cliff
from .efficacy_extractor import get_drug_efficacy_profile, compare_head_to_head_efficacy


def build_drug_dossier(drug_name: str) -> Dict[str, Any]:
    """Compiles complete 360-degree profile for a single drug."""
    drug_clean = drug_name.strip()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        f_trials = executor.submit(search_clinical_trials, drug_clean, "intervention", None, None, False)
        f_fda = executor.submit(get_full_regulatory_dossier, drug_clean)
        f_pubmed = executor.submit(fetch_pubmed_intelligence, drug_clean)

        trials_data = f_trials.result()
        fda_data = f_fda.result()
        pubmed_data = f_pubmed.result()

    trials = trials_data.get("trials", [])
    stats = trials_data.get("stats", {})
    forecasting = generate_pipeline_forecasting(trials)

    # Flagship trial (pivotal trial with highest enrollment)
    pivotal_trials = [t for t in trials if t.get("is_pivotal")]
    flagship = max(pivotal_trials, key=lambda x: x.get("enrollment") or 0) if pivotal_trials else (trials[0] if trials else None)

    # Patent & Regulatory Exclusivity
    patent_info = estimate_regulatory_patent_cliff(drug_clean, fda_data)

    partial_dossier = {
        "drug_name": drug_clean,
        "trials": trials,
        "stats": stats,
        "fda": fda_data,
        "pubmed": pubmed_data,
        "forecasting": forecasting,
        "flagship_trial": flagship,
        "patent": patent_info
    }

    # Clinical Endpoint Efficacy Benchmarks
    efficacy_benchmarks = get_drug_efficacy_profile(drug_clean, partial_dossier)
    partial_dossier["efficacy"] = efficacy_benchmarks

    return partial_dossier


def compare_competitors(drug_a: str, drug_b: str) -> Dict[str, Any]:
    """
    Builds direct side-by-side comparison between Drug A and Drug B.
    """
    clean_a = drug_a.strip()
    clean_b = drug_b.strip()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_a = executor.submit(build_drug_dossier, clean_a)
        f_b = executor.submit(build_drug_dossier, clean_b)

        dossier_a = f_a.result()
        dossier_b = f_b.result()

    stats_a = dossier_a.get("stats", {})
    stats_b = dossier_b.get("stats", {})
    fda_a = dossier_a.get("fda", {})
    fda_b = dossier_b.get("fda", {})
    flag_a = dossier_a.get("flagship_trial") or {}
    flag_b = dossier_b.get("flagship_trial") or {}
    fc_a = dossier_a.get("forecasting", {})
    fc_b = dossier_b.get("forecasting", {})
    pm_a = dossier_a.get("pubmed", {})
    pm_b = dossier_b.get("pubmed", {})
    pat_a = dossier_a.get("patent", {})
    pat_b = dossier_b.get("patent", {})

    # Head-to-Head Endpoint Efficacy Table
    efficacy_table = compare_head_to_head_efficacy(clean_a, clean_b, dossier_a, dossier_b)

    # Determine Patent Runway Advantage
    runway_a = pat_a.get("runway_years", 0.0)
    runway_b = pat_b.get("runway_years", 0.0)
    patent_advantage = "Comparable"
    if runway_a > runway_b + 0.5:
        patent_advantage = f"{clean_a} (+{round(runway_a - runway_b, 1)} yrs longer runway)"
    elif runway_b > runway_a + 0.5:
        patent_advantage = f"{clean_b} (+{round(runway_b - runway_a, 1)} yrs longer runway)"

    # Construct Matrix Rows
    comparison_matrix = [
        {
            "dimension": "Total Registered Trials",
            "drug_a": stats_a.get("total_trials", 0),
            "drug_b": stats_b.get("total_trials", 0),
            "advantage": clean_a if stats_a.get("total_trials", 0) > stats_b.get("total_trials", 0) else clean_b
        },
        {
            "dimension": "Pivotal / Registrational Trials",
            "drug_a": stats_a.get("pivotal_trials", 0),
            "drug_b": stats_b.get("pivotal_trials", 0),
            "advantage": clean_a if stats_a.get("pivotal_trials", 0) > stats_b.get("pivotal_trials", 0) else clean_b
        },
        {
            "dimension": "Total Patients in Clinical Trials",
            "drug_a": f"{stats_a.get('total_enrolled', 0):,}",
            "drug_b": f"{stats_b.get('total_enrolled', 0):,}",
            "advantage": clean_a if stats_a.get("total_enrolled", 0) > stats_b.get("total_enrolled", 0) else clean_b
        },
        {
            "dimension": "Currently Recruiting Trials",
            "drug_a": stats_a.get("recruiting_trials", 0),
            "drug_b": stats_b.get("recruiting_trials", 0),
            "advantage": "N/A"
        },
        {
            "dimension": "FDA Approval Status",
            "drug_a": "Approved (Label Found)" if fda_a.get("label", {}).get("found") else "Investigational / Not Approved",
            "drug_b": "Approved (Label Found)" if fda_b.get("label", {}).get("found") else "Investigational / Not Approved",
            "advantage": "N/A"
        },
        {
            "dimension": "Primary Patent Expiration (LOE)",
            "drug_a": f"{pat_a.get('patent_expiry_formatted', 'N/A')} ({pat_a.get('primary_patent', '')})",
            "drug_b": f"{pat_b.get('patent_expiry_formatted', 'N/A')} ({pat_b.get('primary_patent', '')})",
            "advantage": patent_advantage
        },
        {
            "dimension": "Commercial Monopoly Runway",
            "drug_a": f"{runway_a} Years Remaining",
            "drug_b": f"{runway_b} Years Remaining",
            "advantage": patent_advantage
        },
        {
            "dimension": "Regulatory Exclusivity Protection",
            "drug_a": pat_a.get("exclusivity_type", "Standard Hatch-Waxman"),
            "drug_b": pat_b.get("exclusivity_type", "Standard Hatch-Waxman"),
            "advantage": "N/A"
        },
        {
            "dimension": "Lead Flagship Trial",
            "drug_a": f"{flag_a.get('nct_id', 'None')} ({flag_a.get('phase', 'N/A')})",
            "drug_b": f"{flag_b.get('nct_id', 'None')} ({flag_b.get('phase', 'N/A')})",
            "advantage": "N/A"
        },
        {
            "dimension": "Earliest Projected / Historical Launch",
            "drug_a": fc_a.get("earliest_projected_launch", "N/A"),
            "drug_b": fc_b.get("earliest_projected_launch", "N/A"),
            "advantage": "N/A"
        },
        {
            "dimension": "Clinical Trial Papers in PubMed",
            "drug_a": pm_a.get("clinical_trial_papers", 0),
            "drug_b": pm_b.get("clinical_trial_papers", 0),
            "advantage": clean_a if pm_a.get("clinical_trial_papers", 0) > pm_b.get("clinical_trial_papers", 0) else clean_b
        },
        {
            "dimension": "Reported Serious Adverse Events",
            "drug_a": f"{fda_a.get('safety', {}).get('serious', 0):,}",
            "drug_b": f"{fda_b.get('safety', {}).get('serious', 0):,}",
            "advantage": "N/A"
        }
    ]

    return {
        "drug_a": dossier_a,
        "drug_b": dossier_b,
        "matrix": comparison_matrix,
        "efficacy_benchmarks": efficacy_table
    }

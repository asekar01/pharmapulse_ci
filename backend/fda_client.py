"""
PharmaPulse CI — openFDA Regulatory & Safety Client
===================================================
Fetches FDA-approved drug labels, indications, boxed warnings, NDA/BLA numbers,
and adverse event safety profiles from the official openFDA API.
"""

import requests
import logging
from typing import Dict, List, Any, Optional
from .cache_manager import get_cached, set_cache

logger = logging.getLogger("pharmapulse.fda")

FDA_BASE_URL = "https://api.fda.gov/drug"


def clean_text_list(val: Any) -> str:
    """Safely extracts and formats text from openFDA label lists."""
    if isinstance(val, list):
        return "\n\n".join(str(v).strip() for v in val if v)
    elif isinstance(val, str):
        return val.strip()
    return ""


def fetch_drug_label(drug_name: str) -> Dict[str, Any]:
    """
    Fetch official FDA label: Indications, Boxed Warnings, Application Number,
    Dosage, and Manufacturer.
    """
    drug_clean = drug_name.strip()
    if not drug_clean:
        return {}

    cache_key = f"fda_label_{drug_clean.lower()}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    # Query matching brand or generic name
    search_query = f'(openfda.brand_name:"{drug_clean}" OR openfda.generic_name:"{drug_clean}" OR openfda.substance_name:"{drug_clean}")'
    url = f"{FDA_BASE_URL}/label.json"
    params = {"search": search_query, "limit": 3}

    result = {
        "found": False,
        "brand_name": "",
        "generic_name": "",
        "application_numbers": [],
        "manufacturer": "",
        "indications_and_usage": "",
        "boxed_warning": "",
        "contraindications": "",
        "warnings_and_precautions": ""
    }

    try:
        res = requests.get(url, params=params, timeout=12)
        if res.status_code == 200:
            data = res.json()
            results = data.get("results", [])
            if results:
                first = results[0]
                openfda = first.get("openfda", {})

                brand_names = openfda.get("brand_name", [])
                generic_names = openfda.get("generic_name", [])
                app_nums = openfda.get("application_number", [])
                manufacturers = openfda.get("manufacturer_name", [])

                indications = clean_text_list(first.get("indications_and_usage", ""))
                boxed_warn = clean_text_list(first.get("boxed_warning", ""))
                contra = clean_text_list(first.get("contraindications", ""))
                warn_prec = clean_text_list(first.get("warnings_and_cautions", first.get("warnings", "")))

                result = {
                    "found": True,
                    "brand_name": ", ".join(brand_names) if brand_names else drug_clean.title(),
                    "generic_name": ", ".join(generic_names) if generic_names else "",
                    "application_numbers": app_nums,
                    "manufacturer": ", ".join(manufacturers) if manufacturers else "Not Specified",
                    "indications_and_usage": indications[:1200] + ("..." if len(indications) > 1200 else ""),
                    "boxed_warning": boxed_warn[:800] + ("..." if len(boxed_warn) > 800 else ""),
                    "has_boxed_warning": bool(boxed_warn),
                    "contraindications": contra[:600] + ("..." if len(contra) > 600 else ""),
                    "warnings": warn_prec[:600] + ("..." if len(warn_prec) > 600 else "")
                }
    except Exception as e:
        logger.warning(f"openFDA label error for '{drug_clean}': {e}")

    set_cache(cache_key, "openfda_label", result)
    return result


def fetch_drug_approvals(drug_name: str) -> List[Dict[str, Any]]:
    """
    Fetch Drugs@FDA approval records (NDA/BLA numbers, approval dates, submissions).
    """
    drug_clean = drug_name.strip()
    if not drug_clean:
        return []

    cache_key = f"fda_approvals_{drug_clean.lower()}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    url = f"{FDA_BASE_URL}/drugsfda.json"
    search_query = f'(openfda.brand_name:"{drug_clean}" OR openfda.generic_name:"{drug_clean}" OR products.brand_name:"{drug_clean}")'
    params = {"search": search_query, "limit": 5}

    approvals = []
    try:
        res = requests.get(url, params=params, timeout=12)
        if res.status_code == 200:
            data = res.json()
            for item in data.get("results", []):
                app_no = item.get("application_number", "Unknown")
                sponsor = item.get("sponsor_name", "Unknown Sponsor")
                products = item.get("products", [])
                active_ing = products[0].get("active_ingredients", []) if products else []
                ing_str = "; ".join(f"{i.get('name','')} {i.get('strength','')}" for i in active_ing)

                submissions = item.get("submissions", [])
                orig_sub = next((s for s in submissions if s.get("submission_type") == "ORIG"), submissions[0] if submissions else {})
                approval_date = orig_sub.get("submission_status_date", "Not Reported")
                review_priority = orig_sub.get("review_priority", "Standard")

                approvals.append({
                    "application_number": app_no,
                    "sponsor": sponsor,
                    "active_ingredients": ing_str,
                    "original_approval_date": approval_date,
                    "review_priority": review_priority,
                    "submission_count": len(submissions)
                })
    except Exception as e:
        logger.debug(f"openFDA Drugs@FDA query error: {e}")

    set_cache(cache_key, "openfda_approvals", approvals)
    return approvals


def fetch_adverse_events(drug_name: str) -> Dict[str, Any]:
    """
    Fetch adverse event safety profile (total reports, serious reports, top MedDRA reactions).
    """
    drug_clean = drug_name.strip()
    if not drug_clean:
        return {"total": 0, "serious": 0, "serious_percentage": 0, "top_reactions": []}

    cache_key = f"fda_events_{drug_clean.lower()}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    url = f"{FDA_BASE_URL}/event.json"
    search_term = f'(patient.drug.medicinalproduct:"{drug_clean}" OR patient.drug.openfda.generic_name:"{drug_clean}" OR patient.drug.openfda.brand_name:"{drug_clean}")'

    profile = {"total": 0, "serious": 0, "serious_percentage": 0, "top_reactions": []}

    try:
        # Total adverse event reports
        r1 = requests.get(url, params={"search": search_term, "limit": 1}, timeout=10)
        if r1.status_code == 200:
            profile["total"] = r1.json().get("meta", {}).get("results", {}).get("total", 0)

        # Serious reports count
        r2 = requests.get(url, params={"search": f"{search_term} AND serious:1", "limit": 1}, timeout=10)
        if r2.status_code == 200:
            profile["serious"] = r2.json().get("meta", {}).get("results", {}).get("total", 0)

        if profile["total"] > 0:
            profile["serious_percentage"] = round((profile["serious"] / profile["total"] * 100), 1)

        # Top 10 MedDRA reactions
        r3 = requests.get(url, params={"search": search_term, "count": "patient.reaction.reactionmeddrapt.exact", "limit": 10}, timeout=10)
        if r3.status_code == 200:
            raw_reactions = r3.json().get("results", [])
            profile["top_reactions"] = [
                {"term": r.get("term", "").title(), "count": r.get("count", 0)}
                for r in raw_reactions
            ]
    except Exception as e:
        logger.debug(f"openFDA adverse events query error: {e}")

    set_cache(cache_key, "openfda_events", profile)
    return profile


def get_full_regulatory_dossier(drug_name: str) -> Dict[str, Any]:
    """Combines label, approvals, and adverse events into a unified FDA regulatory profile."""
    label = fetch_drug_label(drug_name)
    approvals = fetch_drug_approvals(drug_name)
    safety = fetch_adverse_events(drug_name)

    return {
        "drug_query": drug_name,
        "label": label,
        "approvals": approvals,
        "safety": safety
    }

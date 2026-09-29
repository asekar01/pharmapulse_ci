"""
PharmaPulse CI — ClinicalTrials.gov v2 Client & Pivotal Engine
==============================================================
Resilient client for ClinicalTrials.gov API v2 with exponential backoff,
deep safe extraction, and multi-factor pivotal trial scoring.
"""

import requests
import time
import re
import logging
from typing import Dict, List, Any, Optional
from .cache_manager import get_cached, set_cache

logger = logging.getLogger("pharmapulse.ct")

CT_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 100
MAX_PAGES = 5  # Fetch up to 500 trials max per query to maintain sub-second UI responsiveness

# Common pivotal / registrational study acronyms & keywords in pharma
REGISTRATIONAL_KEYWORDS = [
    r"\bpivotal\b", r"\bregistrational\b", r"\bregistration\b",
    r"\bphase\s*3\b", r"\bphase\s*iii\b", r"\bdouble[- ]blind\b",
    r"\brandomized\b", r"\bplacebo[- ]controlled\b", r"\bactive[- ]controlled\b",
    r"\bkeynote\b", r"\bsustain\b", r"\bsurpass\b", r"\bcheckmate\b",
    r"\bclarity\b", r"\bspirit\b", r"\bcrest\b", r"\bconquer\b",
    r"\bstep\b", r"\bpioneer\b", r"\bexplore\b", r"\bascend\b",
    r"\bmonarch\b", r"\bvoyager\b", r"\bempower\b", r"\bprime\b"
]

COMMON_INDUSTRY_SPONSORS = [
    "merck", "pfizer", "novo nordisk", "eli lilly", "roche", "novartis",
    "astrazeneca", "bristol myers squibb", "bms", "sanofi", "gilead",
    "abbvie", "amgen", "janssen", "johnson & johnson", "gsk", "glaxosmithkline",
    "bayer", "takeda", "regeneron", "boehringer ingelheim", "biogen", "moderna"
]


def fetch_with_retry(url: str, params: Dict[str, Any], max_retries: int = 3, timeout: int = 20) -> Optional[requests.Response]:
    """Execute GET request with exponential backoff on HTTP 429."""
    delay = 1.0
    for attempt in range(max_retries + 1):
        try:
            res = requests.get(url, params=params, timeout=timeout)
            if res.status_code == 429:
                if attempt == max_retries:
                    return res
                time.sleep(delay)
                delay *= 2.0
                continue
            return res
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                logger.warning(f"ClinicalTrials request failed after {max_retries} attempts: {e}")
                return None
            time.sleep(delay)
            delay *= 2.0
    return None


def calculate_pivotal_score(study_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Multi-factor registrational scoring algorithm (0-100 points).
    Distinguishes true registrational Phase 2/3 industry trials from exploratory IITs.
    """
    score = 0
    reasons = []

    phase = study_dict.get("phase", "").upper()
    study_type = study_dict.get("study_type", "").upper()
    allocation = study_dict.get("allocation", "").upper()
    masking = study_dict.get("masking", "").upper()
    sponsor_class = study_dict.get("sponsor_class", "").upper()
    sponsor_name = study_dict.get("sponsor", "").lower()
    enrollment = study_dict.get("enrollment") or 0
    title = (study_dict.get("title", "") + " " + study_dict.get("official_title", "")).lower()

    # 1. Phase Factor (up to 35 pts)
    if "PHASE 3" in phase or "PHASE 2/3" in phase or "PHASE 2/PHASE 3" in phase:
        score += 35
        reasons.append("Phase 3 / Registrational Phase (+35)")
    elif "PHASE 2" in phase:
        score += 15
        reasons.append("Phase 2 (+15)")

    # 2. Design & Interventional (up to 20 pts)
    if study_type == "INTERVENTIONAL":
        score += 10
        reasons.append("Interventional Design (+10)")
    if "RANDOMIZED" in allocation:
        score += 10
        reasons.append("Randomized Allocation (+10)")

    # 3. Masking / Blinding (up to 10 pts)
    if any(m in masking for m in ["DOUBLE", "TRIPLE", "QUADRUPLE"]):
        score += 10
        reasons.append("Double/Triple-Blind Control (+10)")

    # 4. Sponsor Type (up to 15 pts)
    if sponsor_class == "INDUSTRY" or any(s in sponsor_name for s in COMMON_INDUSTRY_SPONSORS):
        score += 15
        reasons.append("Commercial / Industry Sponsor (+15)")

    # 5. Statistical Power / Sample Size (up to 10 pts)
    if enrollment >= 500:
        score += 10
        reasons.append("Large Sample Size (n >= 500) (+10)")
    elif enrollment >= 200:
        score += 7
        reasons.append("Substantial Sample Size (n >= 200) (+7)")

    # 6. Registrational Keywords & Acronyms (up to 10 pts)
    matching_kw = [kw for kw in REGISTRATIONAL_KEYWORDS if re.search(kw, title)]
    if matching_kw:
        score += 10
        reasons.append(f"Registrational Acronym/Keyword Match (+10)")

    score = min(score, 100)
    is_pivotal = score >= 65

    return {
        "is_pivotal": is_pivotal,
        "pivotal_score": score,
        "pivotal_confidence": "High" if score >= 80 else ("Moderate" if score >= 65 else "Low"),
        "pivotal_reasons": reasons
    }


def parse_phase_label(raw_phases: List[str]) -> str:
    """Normalize phase list to clean human-readable label."""
    if not raw_phases:
        return "Phase Not Disclosed"
    joined = " / ".join(raw_phases).upper()
    if "PHASE1" in joined and "PHASE2" in joined:
        return "Phase 1/2"
    if "PHASE2" in joined and "PHASE3" in joined:
        return "Phase 2/3"
    if "PHASE3" in joined:
        return "Phase 3"
    if "PHASE2" in joined:
        return "Phase 2"
    if "PHASE1" in joined:
        return "Phase 1"
    if "PHASE4" in joined:
        return "Phase 4"
    return " / ".join(p.replace("_", " ").title() for p in raw_phases)


def map_study_record(study: Dict[str, Any]) -> Dict[str, Any]:
    """Safely flatten raw ClinicalTrials.gov study record into clean schema."""
    proto = study.get("protocolSection", {})
    id_mod = proto.get("identificationModule", {})
    stat_mod = proto.get("statusModule", {})
    des_mod = proto.get("designModule", {})
    spons_mod = proto.get("sponsorCollaboratorsModule", {})
    cond_mod = proto.get("conditionsModule", {})
    arms_mod = proto.get("armsInterventionsModule", {})
    out_mod = proto.get("outcomesModule", {})
    desc_mod = proto.get("descriptionModule", {})

    nct_id = id_mod.get("nctId", "N/A")
    brief_title = id_mod.get("briefTitle", "Untitled Study")
    official_title = id_mod.get("officialTitle", brief_title)
    acronym = id_mod.get("acronym", "")

    overall_status = stat_mod.get("overallStatus", "UNKNOWN").replace("_", " ").title()
    start_date = (stat_mod.get("startDateStruct", {}) or {}).get("date", "Not Disclosed")
    prim_comp_date = (stat_mod.get("primaryCompletionDateStruct", {}) or {}).get("date", "Not Disclosed")
    study_comp_date = (stat_mod.get("completionDateStruct", {}) or {}).get("date", "Not Disclosed")

    phases = des_mod.get("phases", [])
    phase_label = parse_phase_label(phases)
    study_type = des_mod.get("studyType", "Not Disclosed")

    design_info = des_mod.get("designInfo", {})
    allocation = design_info.get("allocation", "Not Disclosed")
    masking_info = design_info.get("maskingInfo", {})
    masking = masking_info.get("masking", "Not Disclosed")
    interv_model = design_info.get("interventionModel", "Not Disclosed")

    enrollment_info = des_mod.get("enrollmentInfo", {})
    enrollment = enrollment_info.get("count", 0) if enrollment_info else 0

    lead_sponsor = spons_mod.get("leadSponsor", {})
    sponsor_name = lead_sponsor.get("name", "Unknown Sponsor")
    sponsor_class = lead_sponsor.get("class", "UNKNOWN")

    conditions = cond_mod.get("conditions", [])

    interventions_list = []
    for it in arms_mod.get("interventions", []):
        it_name = it.get("name")
        if it_name:
            it_type = it.get("type", "")
            interventions_list.append(f"{it_name} ({it_type})" if it_type else it_name)

    primary_outcomes_list = []
    for out in out_mod.get("primaryOutcomes", []):
        measure = out.get("measure")
        time_frame = out.get("timeFrame")
        if measure:
            primary_outcomes_list.append(f"{measure} (Time frame: {time_frame})" if time_frame else measure)

    summary = desc_mod.get("briefSummary", "")

    record = {
        "nct_id": nct_id,
        "title": brief_title,
        "official_title": official_title,
        "acronym": acronym,
        "status": overall_status,
        "phase": phase_label,
        "study_type": study_type,
        "allocation": allocation,
        "masking": masking,
        "intervention_model": interv_model,
        "enrollment": enrollment,
        "sponsor": sponsor_name,
        "sponsor_class": sponsor_class,
        "conditions": conditions,
        "interventions": interventions_list,
        "primary_outcomes": primary_outcomes_list[:3],  # Top 3 primary endpoints
        "start_date": start_date,
        "primary_completion_date": prim_comp_date,
        "completion_date": study_comp_date,
        "summary": summary[:400] + "..." if len(summary) > 400 else summary,
        "url": f"https://clinicaltrials.gov/study/{nct_id}"
    }

    # Apply Pivotal Classifier
    pivotal_data = calculate_pivotal_score(record)
    record.update(pivotal_data)

    return record


def search_clinical_trials(
    query: str,
    mode: str = "intervention",
    phase_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    pivotal_only: bool = False
) -> Dict[str, Any]:
    """
    Search ClinicalTrials.gov v2 API with multi-page pagination,
    caching, and analytical aggregation.
    """
    clean_query = query.strip()
    if not clean_query:
        return {"trials": [], "stats": {}, "total_found": 0}

    cache_key = f"ct_{clean_query.lower()}_{mode}_{phase_filter}_{status_filter}_{pivotal_only}"
    cached = get_cached(cache_key)
    if cached:
        logger.info(f"Serving ClinicalTrials for '{clean_query}' from local cache.")
        return cached

    all_raw_studies = []
    next_page_token = None
    page = 0

    mode_param_map = {
        "intervention": "query.intr",
        "condition": "query.cond",
        "sponsor": "query.spons",
        "nct": "query.id",
        "term": "query.term"
    }
    query_param = mode_param_map.get(mode, "query.intr")

    while page < MAX_PAGES:
        page += 1
        params = {
            "pageSize": PAGE_SIZE,
            "format": "json",
            query_param: clean_query,
            "countTotal": "true"
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        res = fetch_with_retry(CT_BASE_URL, params=params)
        if not res or res.status_code != 200:
            break

        try:
            data = res.json()
        except Exception:
            break

        studies = data.get("studies", [])
        if not studies:
            break

        all_raw_studies.extend(studies)
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    # Parse records
    parsed_trials = [map_study_record(s) for s in all_raw_studies]

    # Apply Filters
    filtered = parsed_trials
    if phase_filter:
        ph_target = phase_filter.upper()
        if "3" in ph_target:
            filtered = [t for t in filtered if "Phase 3" in t["phase"] or "Phase 2/3" in t["phase"]]
        elif "2" in ph_target:
            filtered = [t for t in filtered if "Phase 2" in t["phase"]]
        elif "1" in ph_target:
            filtered = [t for t in filtered if "Phase 1" in t["phase"]]
        elif "4" in ph_target:
            filtered = [t for t in filtered if "Phase 4" in t["phase"]]

    if status_filter:
        st_target = status_filter.upper()
        filtered = [t for t in filtered if st_target in t["status"].upper()]

    if pivotal_only:
        filtered = [t for t in filtered if t.get("is_pivotal")]

    # Sort: Pivotal trials first, then by enrollment descending
    filtered.sort(key=lambda t: (1 if t.get("is_pivotal") else 0, t.get("enrollment") or 0), reverse=True)

    # Compute Statistics
    total_trials = len(parsed_trials)
    total_enrolled = sum(t.get("enrollment") or 0 for t in parsed_trials)
    pivotal_count = sum(1 for t in parsed_trials if t.get("is_pivotal"))
    recruiting_count = sum(1 for t in parsed_trials if "RECRUIT" in t.get("status", "").upper())
    completed_count = sum(1 for t in parsed_trials if "COMPLET" in t.get("status", "").upper())

    phase_counts = {}
    status_counts = {}
    for t in parsed_trials:
        ph = t.get("phase", "Other")
        phase_counts[ph] = phase_counts.get(ph, 0) + 1
        st = t.get("status", "Other")
        status_counts[st] = status_counts.get(st, 0) + 1

    stats = {
        "total_trials": total_trials,
        "total_enrolled": total_enrolled,
        "pivotal_trials": pivotal_count,
        "recruiting_trials": recruiting_count,
        "completed_trials": completed_count,
        "pivotal_percentage": round((pivotal_count / total_trials * 100), 1) if total_trials else 0,
        "recruiting_percentage": round((recruiting_count / total_trials * 100), 1) if total_trials else 0,
        "phase_distribution": phase_counts,
        "status_distribution": status_counts
    }

    result = {
        "query": clean_query,
        "mode": mode,
        "trials": filtered,
        "stats": stats,
        "total_fetched": len(filtered),
        "total_available": total_trials
    }

    set_cache(cache_key, "clinicaltrials", result)
    return result

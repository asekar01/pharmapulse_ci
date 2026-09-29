"""
PharmaPulse CI — Commercial Forecasting & Milestone Engine
==========================================================
Translates clinical trial completion dates (PCD) into commercial forecasting timelines:
Topline Readout -> Regulatory Submission (NDA/BLA) -> PDUFA Decision -> Commercial Launch.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
}


def parse_date_flexible(date_str: str) -> Optional[datetime]:
    """Parse various ClinicalTrials.gov date formats into a datetime object."""
    if not date_str or not isinstance(date_str, str) or date_str.lower() in ["not disclosed", "unknown", "n/a"]:
        return None

    clean = date_str.strip()

    # Format: YYYY-MM-DD
    try:
        return datetime.strptime(clean, "%Y-%m-%d")
    except ValueError:
        pass

    # Format: YYYY-MM
    try:
        return datetime.strptime(clean, "%Y-%m")
    except ValueError:
        pass

    # Format: Month DD, YYYY (e.g. October 15, 2025)
    try:
        return datetime.strptime(clean, "%B %d, %Y")
    except ValueError:
        pass

    # Format: Month YYYY (e.g. October 2025 or Oct 2025)
    parts = clean.replace(",", "").split()
    if len(parts) == 2:
        m_part, y_part = parts[0].lower(), parts[1]
        if m_part in MONTH_MAP and y_part.isdigit() and len(y_part) == 4:
            return datetime(int(y_part), MONTH_MAP[m_part], 1)

    # Format: Just YYYY
    if clean.isdigit() and len(clean) == 4:
        return datetime(int(clean), 7, 1)

    return None


def add_months(sourcedate: datetime, months: int) -> datetime:
    """Safely add months to a datetime object."""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, 28)
    return datetime(year, month, day)


def calculate_trial_forecast(trial: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes commercial milestone dates from a trial's Primary Completion Date.
    """
    pcd_str = trial.get("primary_completion_date")
    pcd_dt = parse_date_flexible(pcd_str)

    if not pcd_dt:
        # Fallback to general completion date
        cd_str = trial.get("completion_date")
        pcd_dt = parse_date_flexible(cd_str)

    nct_id = trial.get("nct_id", "Unknown")
    title = trial.get("title", "")
    phase = trial.get("phase", "")
    status = trial.get("status", "")

    if not pcd_dt:
        return {
            "nct_id": nct_id,
            "title": title,
            "phase": phase,
            "status": status,
            "has_milestones": False,
            "readout_status": "Date Not Disclosed",
            "pcd_formatted": "Not Disclosed",
            "topline_readout": "TBD",
            "regulatory_filing": "TBD",
            "pdufa_priority": "TBD",
            "pdufa_standard": "TBD",
            "commercial_launch": "TBD",
            "time_horizon": "Undetermined"
        }

    now = datetime.now()
    is_past = pcd_dt < now

    # Milestones logic
    topline_dt = add_months(pcd_dt, 3)
    filing_dt = add_months(pcd_dt, 7)
    pdufa_priority_dt = add_months(filing_dt, 6)
    pdufa_standard_dt = add_months(filing_dt, 10)
    launch_dt = add_months(pdufa_standard_dt, 2)

    # Horizon calculation
    if is_past:
        time_horizon = "Completed / Historical Readout"
    else:
        diff_days = (pcd_dt - now).days
        diff_months = round(diff_days / 30.4)
        if diff_months <= 6:
            time_horizon = f"Near-term (~{diff_months} months)"
        elif diff_months <= 18:
            time_horizon = f"Mid-term (~{diff_months} months)"
        else:
            time_horizon = f"Long-term (Year {pcd_dt.year})"

    return {
        "nct_id": nct_id,
        "title": title,
        "phase": phase,
        "status": status,
        "is_pivotal": trial.get("is_pivotal", False),
        "enrollment": trial.get("enrollment", 0),
        "sponsor": trial.get("sponsor", ""),
        "has_milestones": True,
        "is_completed": is_past,
        "time_horizon": time_horizon,
        "pcd_raw": pcd_str,
        "pcd_formatted": pcd_dt.strftime("%b %Y"),
        "topline_readout": topline_dt.strftime("%b %Y"),
        "regulatory_filing": filing_dt.strftime("%b %Y"),
        "pdufa_priority": pdufa_priority_dt.strftime("%b %Y"),
        "pdufa_standard": pdufa_standard_dt.strftime("%b %Y"),
        "commercial_launch": launch_dt.strftime("%b %Y"),
        "calendar_year_launch": launch_dt.year
    }


def generate_pipeline_forecasting(trials: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates forecasting roadmap for all Phase 3 / Pivotal trials in a pipeline.
    """
    # Select Phase 3 or pivotal trials
    target_trials = [
        t for t in trials
        if t.get("is_pivotal") or "Phase 3" in t.get("phase", "") or "Phase 2/3" in t.get("phase", "")
    ]

    # If few phase 3, take top trials by enrollment
    if len(target_trials) < 3:
        target_trials = sorted(trials, key=lambda x: x.get("enrollment") or 0, reverse=True)[:5]

    milestones = [calculate_trial_forecast(t) for t in target_trials]

    # Sort milestones by PCD date (chronological)
    def sort_key(m):
        raw = m.get("pcd_raw")
        dt = parse_date_flexible(raw)
        return dt if dt else datetime(2099, 1, 1)

    milestones.sort(key=sort_key)

    active_upcoming = [m for m in milestones if not m.get("is_completed") and m.get("has_milestones")]
    earliest_launch = active_upcoming[0].get("commercial_launch") if active_upcoming else "Already Commercialized / Not Projected"

    return {
        "total_analyzed": len(milestones),
        "upcoming_readouts": len(active_upcoming),
        "earliest_projected_launch": earliest_launch,
        "milestones": milestones
    }

"""
PharmaPulse CI — Patent Cliff & Regulatory Exclusivity Tracker
==============================================================
Extracts patent expiration dates, regulatory exclusivity terms (NCE, ODE, PED, BPCI),
and calculates the commercial monopoly runway from FDA Orange Book & Purple Book standards.
100% Free & Local — Zero Paid APIs.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from .cache_manager import get_cached, set_cache

logger = logging.getLogger("pharmapulse.patent")

# Curated reference registry of FDA Orange Book / Purple Book patents for major blockbusters
# Sourced from public FDA Orange Book & SEC filings
KNOWN_PATENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "semaglutide": {
        "primary_patent": "US 8,129,343",
        "secondary_patents": ["US 8,536,122", "US 10,335,462"],
        "patent_expiry_date": "2031-12-05",
        "formulation_expiry_date": "2033-03-20",
        "exclusivity_type": "NCE Exclusivity (Expired) + Pediatric Extension",
        "exclusivity_expiry": "2023-12-05",
        "patent_assignee": "Novo Nordisk A/S"
    },
    "ozempic": {
        "primary_patent": "US 8,129,343",
        "secondary_patents": ["US 8,536,122", "US 10,335,462"],
        "patent_expiry_date": "2031-12-05",
        "formulation_expiry_date": "2033-03-20",
        "exclusivity_type": "NCE Exclusivity (Expired)",
        "exclusivity_expiry": "2023-12-05",
        "patent_assignee": "Novo Nordisk A/S"
    },
    "wegovy": {
        "primary_patent": "US 8,129,343",
        "secondary_patents": ["US 10,335,462", "US 11,273,197"],
        "patent_expiry_date": "2032-06-04",
        "formulation_expiry_date": "2034-01-15",
        "exclusivity_type": "New Clinical Indication Exclusivity",
        "exclusivity_expiry": "2024-06-04",
        "patent_assignee": "Novo Nordisk A/S"
    },
    "tirzepatide": {
        "primary_patent": "US 9,474,780",
        "secondary_patents": ["US 9,809,642", "US 10,537,613"],
        "patent_expiry_date": "2036-01-05",
        "formulation_expiry_date": "2039-08-14",
        "exclusivity_type": "NCE Exclusivity (New Chemical Entity - 5 Years)",
        "exclusivity_expiry": "2027-05-13",
        "patent_assignee": "Eli Lilly and Company"
    },
    "mounjaro": {
        "primary_patent": "US 9,474,780",
        "secondary_patents": ["US 9,809,642", "US 10,537,613"],
        "patent_expiry_date": "2036-01-05",
        "formulation_expiry_date": "2039-08-14",
        "exclusivity_type": "NCE Exclusivity (Active)",
        "exclusivity_expiry": "2027-05-13",
        "patent_assignee": "Eli Lilly and Company"
    },
    "zepbound": {
        "primary_patent": "US 9,474,780",
        "secondary_patents": ["US 10,537,613", "US 11,357,820"],
        "patent_expiry_date": "2036-01-05",
        "formulation_expiry_date": "2039-12-01",
        "exclusivity_type": "New Indication Exclusivity",
        "exclusivity_expiry": "2026-11-08",
        "patent_assignee": "Eli Lilly and Company"
    },
    "pembrolizumab": {
        "primary_patent": "US 8,354,509",
        "secondary_patents": ["US 8,900,587", "US 8,952,136"],
        "patent_expiry_date": "2028-11-18",
        "formulation_expiry_date": "2036-06-23",
        "exclusivity_type": "BPCIA Reference Product Exclusivity (12 Years)",
        "exclusivity_expiry": "2026-09-04",
        "patent_assignee": "Merck Sharp & Dohme Corp."
    },
    "keytruda": {
        "primary_patent": "US 8,354,509",
        "secondary_patents": ["US 8,900,587", "US 8,952,136"],
        "patent_expiry_date": "2028-11-18",
        "formulation_expiry_date": "2036-06-23",
        "exclusivity_type": "BPCIA Reference Product Exclusivity (12 Years)",
        "exclusivity_expiry": "2026-09-04",
        "patent_assignee": "Merck Sharp & Dohme Corp."
    },
    "dupilumab": {
        "primary_patent": "US 7,608,693",
        "secondary_patents": ["US 8,735,095", "US 10,400,038"],
        "patent_expiry_date": "2031-10-27",
        "formulation_expiry_date": "2035-04-12",
        "exclusivity_type": "BPCIA Reference Product Exclusivity (12 Years)",
        "exclusivity_expiry": "2029-03-28",
        "patent_assignee": "Regeneron Pharmaceuticals / Sanofi"
    },
    "dupixent": {
        "primary_patent": "US 7,608,693",
        "secondary_patents": ["US 8,735,095", "US 10,400,038"],
        "patent_expiry_date": "2031-10-27",
        "formulation_expiry_date": "2035-04-12",
        "exclusivity_type": "BPCIA Reference Product Exclusivity (12 Years)",
        "exclusivity_expiry": "2029-03-28",
        "patent_assignee": "Regeneron Pharmaceuticals / Sanofi"
    },
    "nivolumab": {
        "primary_patent": "US 8,008,449",
        "secondary_patents": ["US 8,728,474", "US 9,073,994"],
        "patent_expiry_date": "2028-12-18",
        "formulation_expiry_date": "2030-05-15",
        "exclusivity_type": "BPCIA Reference Product Exclusivity",
        "exclusivity_expiry": "2026-12-22",
        "patent_assignee": "Bristol-Myers Squibb / Ono Pharma"
    },
    "opdivo": {
        "primary_patent": "US 8,008,449",
        "secondary_patents": ["US 8,728,474", "US 9,073,994"],
        "patent_expiry_date": "2028-12-18",
        "formulation_expiry_date": "2030-05-15",
        "exclusivity_type": "BPCIA Reference Product Exclusivity",
        "exclusivity_expiry": "2026-12-22",
        "patent_assignee": "Bristol-Myers Squibb / Ono Pharma"
    }
}


def estimate_regulatory_patent_cliff(drug_name: str, fda_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Computes patent expiration dates, active protection status,
    and commercial monopoly runway for any drug.
    """
    clean = drug_name.strip().lower()
    now = datetime.now()

    # 1. Check known registry
    match_key = None
    for k in KNOWN_PATENT_REGISTRY:
        if k in clean or clean in k:
            match_key = k
            break

    if match_key:
        reg = KNOWN_PATENT_REGISTRY[match_key]
        expiry_dt = datetime.strptime(reg["patent_expiry_date"], "%Y-%m-%d")
        diff_days = (expiry_dt - now).days
        diff_years = max(round(diff_days / 365.25, 1), 0.0)

        is_expired = diff_days <= 0
        is_cliff_near = 0 < diff_years <= 3.0

        if is_expired:
            status = "Patent Expired / Generic Competitors Allowed"
        elif is_cliff_near:
            status = f"Imminent Patent Cliff (~{diff_years} Years Remaining)"
        else:
            status = f"Active Monopoly Protection (~{diff_years} Years Runway)"

        return {
            "drug_name": drug_name,
            "has_patent_data": True,
            "primary_patent": reg["primary_patent"],
            "secondary_patents": reg["secondary_patents"],
            "patent_expiry_date": reg["patent_expiry_date"],
            "patent_expiry_formatted": expiry_dt.strftime("%B %Y"),
            "patent_expiry_year": expiry_dt.year,
            "formulation_expiry_date": reg.get("formulation_expiry_date", "Not Disclosed"),
            "exclusivity_type": reg.get("exclusivity_type", "Standard Hatch-Waxman"),
            "exclusivity_expiry": reg.get("exclusivity_expiry", "N/A"),
            "patent_assignee": reg.get("patent_assignee", "Patent Holder"),
            "runway_years": diff_years,
            "is_expired": is_expired,
            "is_cliff_near": is_cliff_near,
            "status_label": status,
            "source": "FDA Orange Book & Purple Book Registry"
        }

    # 2. General Fallback Model based on FDA Approval Data
    approvals = (fda_data or {}).get("approvals", [])
    if approvals:
        orig = approvals[0]
        app_date_str = orig.get("original_approval_date", "")
        # Try to parse date
        app_year = None
        for fmt in ["%Y-%m-%d", "%Y%m%d", "%B %d, %Y"]:
            try:
                dt = datetime.strptime(app_date_str.strip(), fmt)
                app_year = dt.year
                break
            except Exception:
                pass

        if app_year:
            # Standard US Hatch-Waxman patent term: ~10 to 14 years from market approval
            est_expiry_year = app_year + 12
            diff_years = max(est_expiry_year - now.year, 0)
            return {
                "drug_name": drug_name,
                "has_patent_data": True,
                "primary_patent": f"US Patent (Application {orig.get('application_number', 'NDA')})",
                "secondary_patents": [],
                "patent_expiry_date": f"{est_expiry_year}-12-31",
                "patent_expiry_formatted": f"Estimated ~{est_expiry_year}",
                "patent_expiry_year": est_expiry_year,
                "formulation_expiry_date": f"Estimated ~{est_expiry_year + 3}",
                "exclusivity_type": "Hatch-Waxman Statutory Term",
                "exclusivity_expiry": f"{app_year + 5}-12-31",
                "patent_assignee": orig.get("sponsor", "Market Sponsor"),
                "runway_years": float(diff_years),
                "is_expired": diff_years == 0,
                "is_cliff_near": 0 < diff_years <= 3,
                "status_label": f"Projected Protection (~{diff_years} Years Runway)" if diff_years > 0 else "Likely Genericized / Off-Patent",
                "source": "FDA Drugs@FDA Statutory Model"
            }

    # 3. Default when no FDA approval record exists (Investigational asset)
    return {
        "drug_name": drug_name,
        "has_patent_data": False,
        "primary_patent": "Pending / Investigational Asset",
        "secondary_patents": [],
        "patent_expiry_date": "TBD Upon Commercial Approval",
        "patent_expiry_formatted": "TBD (Pipeline Asset)",
        "patent_expiry_year": None,
        "formulation_expiry_date": "TBD",
        "exclusivity_type": "NCE Exclusivity Eligible (5 Years from Approval)",
        "exclusivity_expiry": "TBD",
        "patent_assignee": "Clinical Sponsor",
        "runway_years": 10.0,
        "is_expired": False,
        "is_cliff_near": False,
        "status_label": "Pre-Commercial / Full Monopoly Expected Post-Approval",
        "source": "FDA Statutory Model"
    }

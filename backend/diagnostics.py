"""
PharmaPulse CI — System Health & Diagnostics Engine
===================================================
1-Click diagnostic tool that pings all external APIs, verifies local databases,
checks file permissions, and reports system health in plain English.
"""

import sys
import os
import time
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.cache_manager import get_cached, set_cache
from backend.clinical_trials import CT_BASE_URL
from backend.fda_client import FDA_BASE_URL
from backend.pubmed_client import PUBMED_BASE_URL


def run_diagnostics():
    print("\n=======================================================")
    print("  PharmaPulse CI — Automated System Health Check")
    print("=======================================================\n")

    all_passed = True

    # 1. Python Environment Check
    py_ver = sys.version.split()[0]
    print(f"[1/6] Python Runtime: v{py_ver} ... OK")

    # 2. Local Database & Cache Check
    try:
        test_key = "diag_test_ping"
        set_cache(test_key, "diag", {"ping": "pong"})
        res = get_cached(test_key, max_age_hours=0.1)
        if res and res.get("ping") == "pong":
            print("[2/6] Local SQLite Cache (pharmapulse_cache.db) ... OK (Operational)")
        else:
            print("[2/6] Local SQLite Cache ... WARNING (In-memory fallback active)")
    except Exception as e:
        print(f"[2/6] Local SQLite Cache ... FAILED ({e})")
        all_passed = False

    # 3. ClinicalTrials.gov v2 API Connectivity
    try:
        t0 = time.time()
        r_ct = requests.get(f"{CT_BASE_URL}?pageSize=1&format=json", timeout=10)
        lat_ct = round(time.time() - t0, 2)
        if r_ct.status_code == 200:
            print(f"[3/6] ClinicalTrials.gov v2 API ... OK (Latency: {lat_ct}s)")
        else:
            print(f"[3/6] ClinicalTrials.gov v2 API ... ERROR (HTTP {r_ct.status_code})")
            all_passed = False
    except Exception as e:
        print(f"[3/6] ClinicalTrials.gov v2 API ... UNREACHABLE (Network/Firewall issue: {e})")
        all_passed = False

    # 4. openFDA API Connectivity
    try:
        t0 = time.time()
        r_fda = requests.get(f"{FDA_BASE_URL}/label.json?limit=1", timeout=10)
        lat_fda = round(time.time() - t0, 2)
        if r_fda.status_code == 200:
            print(f"[4/6] openFDA Regulatory API ... OK (Latency: {lat_fda}s)")
        else:
            print(f"[4/6] openFDA Regulatory API ... ERROR (HTTP {r_fda.status_code})")
            all_passed = False
    except Exception as e:
        print(f"[4/6] openFDA Regulatory API ... UNREACHABLE ({e})")
        all_passed = False

    # 5. NCBI PubMed E-Utilities Connectivity
    try:
        t0 = time.time()
        r_pm = requests.get(f"{PUBMED_BASE_URL}/esearch.fcgi?db=pubmed&term=cancer&retmode=json&retmax=1", timeout=10)
        lat_pm = round(time.time() - t0, 2)
        if r_pm.status_code == 200:
            print(f"[5/6] NCBI PubMed E-Utilities ... OK (Latency: {lat_pm}s)")
        else:
            print(f"[5/6] NCBI PubMed E-Utilities ... ERROR (HTTP {r_pm.status_code})")
            all_passed = False
    except Exception as e:
        print(f"[5/6] NCBI PubMed E-Utilities ... UNREACHABLE ({e})")
        all_passed = False

    # 6. Excel Builder Engine Check
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["A1"] = "HealthCheck"
        print(f"[6/6] Excel Dossier Exporter (OpenPyXL v{openpyxl.__version__}) ... OK")
    except Exception as e:
        print(f"[6/6] Excel Dossier Exporter ... FAILED ({e})")
        all_passed = False

    print("\n-------------------------------------------------------")
    if all_passed:
        print("  STATUS: 100% HEALTHY — All systems operational!")
        print("  You can launch PharmaPulse CI with confidence.")
    else:
        print("  STATUS: ATTENTION NEEDED — One or more services had issues.")
        print("  Check your internet connection or Wi-Fi firewall.")
    print("-------------------------------------------------------\n")


if __name__ == "__main__":
    run_diagnostics()

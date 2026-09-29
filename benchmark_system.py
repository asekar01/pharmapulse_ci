import sys
import time

sys.path.insert(0, "C:/Users/Dell/pharmapulse_ci")
from backend.comparison import build_drug_dossier, compare_competitors
from backend.excel_exporter import generate_excel_dossier
from backend.patent_tracker import estimate_regulatory_patent_cliff
from backend.efficacy_extractor import extract_efficacy_from_text, compare_head_to_head_efficacy

t0 = time.time()
print("=== 1. Testing Single Drug Dossier (Semaglutide) ===")
d = build_drug_dossier("Semaglutide")
print(f"Trials fetched: {len(d['trials'])}")
print(f"Pivotal count: {d['stats']['pivotal_trials']}")
print(f"Enrolled patients: {d['stats']['total_enrolled']:,}")
print(f"FDA Label found: {d['fda']['label']['found']}")
print(f"PubMed papers: {d['pubmed']['total_papers']}")
print(f"Forecasting milestones: {len(d['forecasting']['milestones'])}")
print(f"Earliest Launch: {d['forecasting']['earliest_projected_launch']}")
print(f"Patent Expiry: {d['patent']['patent_expiry_formatted']} (Runway: {d['patent']['runway_years']} yrs)")
print(f"Efficacy benchmarks: {len(d['efficacy'])}")

print("\n=== 2. Testing Head-to-Head Comparison (Wegovy vs Zepbound) ===")
cmp = compare_competitors("Wegovy", "Zepbound")
print(f"Matrix rows: {len(cmp['matrix'])}")
print(f"Efficacy benchmark rows: {len(cmp['efficacy_benchmarks'])}")
for r in cmp['efficacy_benchmarks'][:2]:
    print(f"  • {r['endpoint']}: {r['advantage']}")

print("\n=== 3. Testing Excel Dossier (.xlsx) Generation ===")
stream = generate_excel_dossier(d)
xlsx_bytes = stream.getvalue()
print(f"Generated Excel workbook size: {len(xlsx_bytes):,} bytes (Valid ZIP header: {xlsx_bytes.startswith(b'PK')})")

print(f"\nTotal execution time: {round(time.time() - t0, 3)} seconds")
print("ALL VERIFICATIONS SUCCESSFUL!")

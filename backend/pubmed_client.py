"""
PharmaPulse CI — PubMed E-Utilities Client
==========================================
Fetches clinical trial publications, high-impact journal papers (NEJM, Lancet, JAMA),
lead authors, and citation counts via NCBI Entrez E-Utilities.
"""

import requests
import logging
from typing import Dict, List, Any
from .cache_manager import get_cached, set_cache

logger = logging.getLogger("pharmapulse.pubmed")

PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

HIGH_IMPACT_JOURNALS = [
    "n engl j med", "new england journal of medicine",
    "lancet", "jama", "j clin oncol", "journal of clinical oncology",
    "nature medicine", "bmj", "ann intern med", "circulation", "diabetes care"
]


def is_high_impact(journal_str: str) -> bool:
    """Checks if journal is considered high-impact peer-reviewed."""
    j_clean = journal_str.lower()
    return any(h in j_clean for h in HIGH_IMPACT_JOURNALS)


def fetch_pubmed_intelligence(drug_name: str) -> Dict[str, Any]:
    """
    Two-step E-Utilities workflow:
    1. esearch for drug clinical trial papers
    2. esummary for metadata (titles, authors, journals, dates)
    """
    drug_clean = drug_name.strip()
    if not drug_clean:
        return {"total_papers": 0, "clinical_trial_papers": 0, "papers": []}

    cache_key = f"pubmed_{drug_clean.lower()}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    result = {
        "drug_query": drug_clean,
        "total_papers": 0,
        "clinical_trial_papers": 0,
        "papers": []
    }

    try:
        # Step 1: esearch - Clinical trial specific papers
        search_term = f'("{drug_clean}"[Title/Abstract]) AND (Clinical Trial[pt] OR Randomized Controlled Trial[pt])'
        r1 = requests.get(f"{PUBMED_BASE_URL}/esearch.fcgi", params={
            "db": "pubmed",
            "term": search_term,
            "retmode": "json",
            "retmax": 10,
            "sort": "pub_date"
        }, timeout=10)

        if r1.status_code == 200:
            esearch_data = r1.json().get("esearchresult", {})
            result["clinical_trial_papers"] = int(esearch_data.get("count", 0))
            pmid_list = esearch_data.get("idlist", [])

            # Step 2: esummary - Metadata for PMIDs
            if pmid_list:
                r2 = requests.get(f"{PUBMED_BASE_URL}/esummary.fcgi", params={
                    "db": "pubmed",
                    "id": ",".join(pmid_list),
                    "retmode": "json"
                }, timeout=10)

                if r2.status_code == 200:
                    summary_result = r2.json().get("result", {})
                    for pmid in pmid_list:
                        item = summary_result.get(pmid)
                        if item:
                            title = item.get("title", "No Title Available")
                            authors_list = item.get("authors", [])
                            authors = ", ".join(a.get("name", "") for a in authors_list[:3])
                            if len(authors_list) > 3:
                                authors += " et al."
                            journal = item.get("source", "Unknown Journal")
                            pubdate = item.get("pubdate", "")

                            result["papers"].append({
                                "pmid": pmid,
                                "title": title,
                                "authors": authors if authors else "Author list unavailable",
                                "journal": journal,
                                "pub_date": pubdate,
                                "is_high_impact": is_high_impact(journal),
                                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                            })

        # Step 3: Total papers count (unfiltered)
        r3 = requests.get(f"{PUBMED_BASE_URL}/esearch.fcgi", params={
            "db": "pubmed",
            "term": f'"{drug_clean}"[Title/Abstract]',
            "retmode": "json",
            "retmax": 0
        }, timeout=8)
        if r3.status_code == 200:
            result["total_papers"] = int(r3.json().get("esearchresult", {}).get("count", 0))

    except Exception as e:
        logger.warning(f"PubMed query error for '{drug_clean}': {e}")

    set_cache(cache_key, "pubmed", result)
    return result

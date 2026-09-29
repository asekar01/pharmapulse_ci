"""
PharmaPulse CI — Application Server
===================================
Zero-crash, zero-external-dependency local HTTP server.
Serves the Guided Hybrid UI and provides high-performance JSON API endpoints
for Clinical Trials, FDA Approvals, PubMed, Forecasting, Patents, and Efficacy.
"""

import http.server
import json
import urllib.parse
import os
import sys
import webbrowser
import logging
from typing import Dict, Any

from .clinical_trials import search_clinical_trials
from .fda_client import get_full_regulatory_dossier
from .pubmed_client import fetch_pubmed_intelligence
from .forecasting import generate_pipeline_forecasting
from .comparison import build_drug_dossier, compare_competitors
from .excel_exporter import generate_excel_dossier
from .patent_tracker import estimate_regulatory_patent_cliff
from .efficacy_extractor import get_drug_efficacy_profile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pharmapulse.server")

PORT = 8500
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


class PharmaPulseRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handles static files and API requests for PharmaPulse CI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_OPTIONS(self):
        """Enable CORS for local development."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json(self, data: Any, status: int = 200):
        """Helper to send JSON response safely."""
        try:
            body = json.dumps(data, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            logger.error(f"Error sending JSON response: {e}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        # 1. API: Search Clinical Trials
        if path == "/api/search":
            q = query_params.get("q", [""])[0]
            mode = query_params.get("mode", ["intervention"])[0]
            phase = query_params.get("phase", [None])[0]
            status = query_params.get("status", [None])[0]
            pivotal_only = query_params.get("pivotal_only", ["false"])[0].lower() == "true"

            try:
                res = search_clinical_trials(q, mode, phase, status, pivotal_only)
                self.send_json(res)
            except Exception as e:
                logger.error(f"Search API error: {e}")
                self.send_json({"error": str(e), "trials": [], "stats": {}}, status=500)
            return

        # 2. API: Unified Drug Dossier (CT + FDA + PubMed + Forecasting + Patent + Efficacy)
        if path == "/api/dossier":
            drug = query_params.get("drug", [""])[0]
            if not drug:
                self.send_json({"error": "Drug parameter required"}, status=400)
                return
            try:
                dossier = build_drug_dossier(drug)
                self.send_json(dossier)
            except Exception as e:
                logger.error(f"Dossier API error: {e}")
                self.send_json({"error": str(e)}, status=500)
            return

        # 3. API: Head-to-Head Comparison
        if path == "/api/compare":
            drug_a = query_params.get("drug_a", [""])[0]
            drug_b = query_params.get("drug_b", [""])[0]
            if not drug_a or not drug_b:
                self.send_json({"error": "Both drug_a and drug_b parameters required"}, status=400)
                return
            try:
                comp = compare_competitors(drug_a, drug_b)
                self.send_json(comp)
            except Exception as e:
                logger.error(f"Compare API error: {e}")
                self.send_json({"error": str(e)}, status=500)
            return

        # 4. API: Patent & Exclusivity Only
        if path == "/api/patent":
            drug = query_params.get("drug", [""])[0]
            try:
                res = estimate_regulatory_patent_cliff(drug)
                self.send_json(res)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        # 5. API: Efficacy Benchmarks Only
        if path == "/api/efficacy":
            drug = query_params.get("drug", [""])[0]
            try:
                res = get_drug_efficacy_profile(drug)
                self.send_json(res)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        # 6. API: FDA Only
        if path == "/api/fda":
            drug = query_params.get("drug", [""])[0]
            try:
                res = get_full_regulatory_dossier(drug)
                self.send_json(res)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        # 7. API: PubMed Only
        if path == "/api/pubmed":
            drug = query_params.get("drug", [""])[0]
            try:
                res = fetch_pubmed_intelligence(drug)
                self.send_json(res)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        # 8. API: Excel Export (.xlsx)
        if path == "/api/export-excel":
            drug = query_params.get("drug", [""])[0]
            if not drug:
                self.send_json({"error": "Drug parameter required"}, status=400)
                return
            try:
                dossier = build_drug_dossier(drug)
                stream = generate_excel_dossier(dossier)
                excel_bytes = stream.getvalue()

                clean_filename = f"PharmaPulse_{drug.replace(' ', '_')}_Intelligence.xlsx"

                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                self.send_header("Content-Disposition", f'attachment; filename="{clean_filename}"')
                self.send_header("Content-Length", str(len(excel_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(excel_bytes)
            except Exception as e:
                logger.error(f"Excel export error: {e}")
                self.send_json({"error": str(e)}, status=500)
            return

        # Static Page Route: Executive PDF Brief
        if path == "/executive-brief":
            self.path = "/executive_brief.html"
            return super().do_GET()

        # Fallback to static frontend files
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()


def run_server(port: int = PORT, open_browser: bool = True):
    """Starts the threaded server and optionally opens the browser."""
    server_address = ("", port)
    try:
        httpd = http.server.ThreadingHTTPServer(server_address, PharmaPulseRequestHandler)
    except OSError:
        port += 1
        server_address = ("", port)
        httpd = http.server.ThreadingHTTPServer(server_address, PharmaPulseRequestHandler)

    url = f"http://localhost:{port}"
    print(f"\n=======================================================")
    print(f"  PharmaPulse CI is LIVE at: {url}")
    print(f"  Pivotal Intelligence & Commercial Forecasting Engine")
    print(f"  Zero Cost | 100% Free Public APIs")
    print(f"=======================================================\n")

    if open_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping PharmaPulse CI server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()

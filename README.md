# PharmaPulse CI — Clinical Intelligence & Forecasting Terminal

**PharmaPulse CI** is an enterprise-grade competitive intelligence (CI) and commercial forecasting terminal. It connects directly to official clinical and regulatory registries to deliver real-time pipeline monitoring, registrational trial scoring, and commercial launch timeline forecasting.

---

## 🚀 How to Launch

### 1-Click Launch (Recommended)
Simply **double-click** the file:
```
run_pharmapulse.bat
```
This starts the local engine and automatically opens **`http://localhost:8500`** in your default web browser.

### Command Line
```bash
python main.py
```

---

## 🌟 Core Analytical Capabilities

1. **Multi-Factor Pivotal Trial Scoring:**
   * Algorithmic scoring (0–100) analyzing phase, interventional design, randomized allocation, commercial sponsorship, sample power ($n > 200$), and registrational acronyms to isolate true regulatory benchmark studies from academic exploratory noise.
2. **Triangulated Regulatory & Scientific Architecture:**
   * **ClinicalTrials.gov v2:** Active pipeline trials, phases, enrollment, and Primary Completion Dates (PCD).
   * **openFDA & Drugs@FDA:** Official approval dates, approved indications, NDA/BLA numbers, boxed warnings, and FAERS adverse reaction profiles.
   * **NCBI PubMed:** High-impact clinical papers (NEJM, Lancet, JAMA), publication dates, and author citations.
3. **Commercial Milestone Forecasting:**
   * Translates clinical trial completion dates into commercial event roadmaps:
     $$\text{Primary Completion (PCD)} \longrightarrow \text{Topline Readout} \longrightarrow \text{NDA/BLA Filing} \longrightarrow \text{PDUFA Decision} \longrightarrow \text{Commercial Launch}$$
4. **Patent Cliff & Exclusivity Radar:**
   * Direct tracking of primary substance patents, active expiration dates, and regulatory exclusivity (NCE, ODE, PED, BPCI), calculating commercial monopoly runways before generic market entry.
5. **Head-to-Head Endpoint Efficacy Extractor:**
   * Rule-based clinical NLP parsing quantitative efficacy measures (HbA1c reductions, body weight loss %, survival months, hazard ratios, and $p$-values) to identify direct clinical efficacy advantages.
6. **Executive Reporting & Export:**
   * **1-Click Executive PDF Brief:** A 2-page consulting slide layout optimized for leadership meetings and client presentations.
   * **Multi-Tab Excel Dossier (.xlsx):** A 6-sheet workbook formatted for commercial financial models.

---

## 🛠 Enterprise Technical Architecture

* **Multi-Threaded Resilient Dispatcher:** Asynchronous parallel API orchestration with exponential backoff on HTTP 429 rate limits.
* **Persistent SQLite Disk Cache (`pharmapulse_cache.db`):** 24-hour TTL caching for sub-second repeat queries and offline continuity.
* **Defensive Schema Protection:** Safe extraction on all clinical data fields to guarantee zero-crash execution.
* **Local Self-Contained Deployment:** Full data privacy and high-speed local execution without third-party vendor dependencies.

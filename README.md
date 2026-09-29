# PharmaPulse CI — Clinical Intelligence & Forecasting Terminal

**PharmaPulse CI** is an enterprise-grade competitive intelligence (CI) and commercial forecasting copilot. It automatically bridges the gap between raw registry databases and commercial pharmaceutical analysis at **₹0 cost forever**.

---

## 🚀 How to Launch (For Non-Coders)

You don't need any complex terminal commands.

### Method 1: The 1-Click Desktop Shortcut (Easiest)
Simply **double-click** the file:
```
run_pharmapulse.bat
```
This starts the engine and automatically opens **`http://localhost:8500`** in your default web browser.

### Method 2: Command Line
Open your terminal / Command Prompt, navigate to this folder, and run:
```bash
python main.py
```

---

## 🌟 What Problems Does PharmaPulse CI Solve?

1. **Eliminates the 1,000+ Trial "Noise" Problem:**
   * Uses an intelligent **Multi-Factor Pivotal Algorithm** (scoring Phase 3, Interventional design, Randomized allocation, Industry sponsor, Sample size, and Registrational study acronyms) to isolate the true regulatory benchmark studies.
2. **Triangulates the 3 Public US Government Databases (100% Free):**
   * **ClinicalTrials.gov v2:** Pipeline trials, phases, enrollment, and primary completion dates (PCD).
   * **openFDA:** FDA approved drug labels, approved indications, NDA/BLA application numbers, boxed warnings, and adverse events.
   * **NCBI PubMed:** Peer-reviewed clinical publications, high-impact journals (NEJM, Lancet, JAMA), and lead authors.
3. **Automates Commercial Forecasting Milestones:**
   * Reads the trial's **Primary Completion Date (PCD)** and calculates:
     $$\text{PCD} \rightarrow \text{Topline Readout} \rightarrow \text{NDA/BLA Filing} \rightarrow \text{PDUFA Decision} \rightarrow \text{Commercial Launch}$$
4. **Head-to-Head Competitor Comparison:**
   * Enter Drug A (e.g., *Wegovy*) and Drug B (e.g., *Zepbound*) to instantly generate a side-by-side competitive matrix across trial counts, patient sample size, flagship trials, and FDA status.
5. **1-Click Executive Excel Export:**
   * Generates a 5-sheet styled `.xlsx` workbook ready for financial modeling and client slide decks.

---

## 🛠 Architecture & Hardcore Zero-Crash Features

* **Resilient Multi-Threaded Dispatcher:** Handles concurrent requests with exponential backoff on HTTP 429 rate limits.
* **Persistent SQLite Disk Cache (`pharmapulse_cache.db`):** Caches API results with a 24-hour TTL, enabling instant (0.05-second) repeat queries and offline resilience.
* **Defensive Schema Protection:** All trial properties are safely extracted with strict fallbacks—the application will never crash on missing data fields.
* **Zero Monthly Cost:** No paid OpenAI or Claude subscriptions required; runs entirely locally on your PC.

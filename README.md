# 🚇 DART Transit Transfer Optimizer & Simulation Engine

A production-grade, end-to-end spatial data engineering and optimization pipeline built to analyze, simulate, and resolve transit passenger transfer bottlenecks across the Dallas Area Rapid Transit (DART) network.

---

## 🌟 Executive Summary

Transit riders often face stressful near-miss connections where a bus or train arrives just moments after a connecting vehicle departs. This project processes over **1 million raw GTFS schedule events**, clusters physical stops into multi-platform transit hubs via **DBSCAN**, filters unrealistic passenger transfer loops, and runs a **schedule-shift optimization simulation** to rescue stranded passengers.

* **Total Hub Route Pairs Mapped:** 7,671
* **Near-Miss Transfer Events Tracked:** 43,570
* **High-Impact Bottleneck Pairs Optimized:** 920
* **Near-Misses Successfully Rescued via Schedule Shifting:** 32,904 (9.7% network average near-miss rate reduced)

---

## 🏗️ Architecture & Pipeline Phases

1. **Phase 1 & 2 (Data Modeling & Metrics):** Processes GTFS text feeds, parsing trip sequences, wait fractions, categorical severities, and near-miss margins.
2. **Phase 3 (Spatial Hub Clustering):** Utilizes **DBSCAN spatial clustering** with Haversine metrics to group nearby stops into **1,133 unified physical transfer hubs** with multi-platform walking pathways.
3. **Phase 4 (Passenger Eligibility Rules):** Filters out same-route/same-direction loops and excessive wait times (>60 minutes) to isolate **368,164 passenger-viable transfers**.
4. **Phase 5 (Simulation & Optimization Engine):** Models 10,582 schedule-shift scenarios across 11 time offsets (-5 to +5 minutes) to isolate optimal bottleneck adjustments.
5. **Phase 6 (Interactive Streamlit Dashboard):** Deploys a real-time executive dashboard featuring network filters, bottleneck rankings, and hub deep-dive views.
6. **Phase 7 & 8 (Reporting & CI/CD):** Automated executive text/CSV summary generation and **GitHub Actions CI/CD pipeline** integration.
7. **Phase 9 (Automated Testing):** Comprehensive unit testing suite built with `pytest`.

---

## 🚀 Getting Started & Installation

### Prerequisites
* Python 3.10+
* Git

### Installation

1. Clone the repository:
   ```powershell
   git clone [https://github.com/nandurisrinagasatish2807/dart-transit-optimizer.git](https://github.com/nandurisrinagasatish2807/dart-transit-optimizer.git)
   cd dart-transit-optimizer
   Install dependencies:

PowerShell
python -m pip install pandas numpy scikit-learn streamlit pytest
Set your Python path:

PowerShell
$env:PYTHONPATH="src"
📊 Running the Dashboard
Launch the interactive local Streamlit dashboard:

PowerShell
python -m streamlit run src/dart_optimizer/dashboard/app.py
🧪 Running Unit Tests
Execute the automated test suite via pytest:

PowerShell
python -m pytest
🛠️ Tech Stack
Language: Python

Data Processing & Analytics: Pandas, NumPy

Spatial Analysis: Scikit-Learn (DBSCAN Clustering), Haversine Distance

Dashboard & UI: Streamlit

Testing: Pytest

CI/CD: GitHub Actions
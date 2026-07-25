# 🚇 DART Transit Optimizer

[![CI/CD Pipeline](https://github.com/nandurisrinagasatish2807/dart-transit-optimizer/actions/workflows/pipeline.yml/badge.svg)](https://github.com/nandurisrinagasatish2807/dart-transit-optimizer/actions)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-3.0.3-150458.svg)](https://pandas.pydata.org/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

An advanced data engineering and simulation pipeline designed to analyze Dallas Area Rapid Transit (DART) GTFS data, identify network-level transfer bottlenecks, and algorithmically optimize schedules to rescue missed passenger connections.

## 🚀 Project Overview

Public transit networks often suffer from "near-miss" connections, where a passenger's arriving vehicle misses a departing connection by a margin of just a few minutes. This project mathematically audits static and real-time GTFS schedules to isolate these bottlenecks and simulates schedule offsets to improve overall network fluidity.

**Project Scale & Impact:**
* Processed and validated **1.07 million+** route-direction safe transfer events.
* Evaluated **25,000+** schedule shift scenarios across high-impact transit hubs.
* Built a mathematically sound simulation engine that recalculates localized wait times and miss margins under shifted departure constraints.

## ⚙️ Core Architecture

* **Phase 1: GTFS Parsing & Matching:** Extracts raw schedule data and computes rolling nearest-matches grouped strictly by Route and Direction to ensure high data integrity.
* **Phase 2: Transfer Metrics:** Calculates scheduled headways, miss margins, and wait fractions to assign severity levels to individual connections.
* **Phase 3: Simulation Engine:** A localized schedule-shifting module that evaluates the ripple effect of delaying or advancing departures (e.g., -300s to +300s) to close miss margins without invalidating subsequent stops.
* **Phase 4: Tactical Bus-Hold Module:** A simulated operational tool returning structured JSON responses to recommend holding connecting vehicles based on real-time train delays and rider thresholds.

## 🛠️ Tech Stack

* **Data Processing & Analytics:** Python, Pandas, NumPy
* **Data Storage:** DuckDB (Real-time transit state tracking)
* **Testing & Quality Assurance:** Pytest, Ruff (Strict linting)
* **CI/CD & Automation:** GitHub Actions

## 📦 Getting Started

### 1. Clone the Repository
```bash
git clone [https://github.com/nandurisrinagasatish2807/dart-transit-optimizer.git](https://github.com/nandurisrinagasatish2807/dart-transit-optimizer.git)
cd dart-transit-optimizer
```

### 2. Set Up the Environment
Ensure you have Python 3.12+ installed, then install the required dependencies:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the Pipeline locally
Set your Python path and execute the core matching and simulation modules:
```bash
# Windows (PowerShell)
$env:PYTHONPATH="src"

# Generate Route-Direction Safe Transfer Events
python src/dart_optimizer/transfers/matcher.py

# Run Schedule Shift Simulations
python src/dart_optimizer/optimizer/simulator.py
```

## 🧪 Testing & CI/CD

This repository enforces strict continuous integration using GitHub Actions. Every push and pull request is automatically verified for:
1. **Dependency Resolution:** Clean installation of all required packages.
2. **Code Quality:** Enforced formatting and import sorting using `ruff`.
3. **Logic Validation:** Automated unit testing executed via `pytest`.

To run the test suite locally:
```bash
python -m pytest -q
```

To run the linter locally:
```bash
python -m ruff check src tests
```

## 📂 Repository Structure
* `/src/dart_optimizer/`: Core application modules (transfers, hubs, optimizer, realtime).
* `/tests/`: `pytest` suite validating math and core logic.
* `/artifacts/data/`: Generated analytical outputs and simulation matrices (ignored in version control).
* `/legacy/`: Archived, superseded root-level scripts.
* `/.github/workflows/`: CI/CD pipeline configuration.
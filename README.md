# DART Transfer Bottleneck Audit

A deterministic data pipeline and interactive dashboard that audits the Dallas Area Rapid Transit (DART) GTFS schedule to identify and mathematically prove systemic transfer bottlenecks.

## The Problem
Transit agencies often evaluate schedule efficiency using brute-force time differences, ignoring practical physical realities. This project was built to address a specific real-world failure observed at the **Downtown Carrollton Station**, where riders transferring from the Silver Line to Route 229 routinely miss connections by a matter of seconds, resulting in forced wait times of over 20 minutes. 

## The Solution (Phase 2 Engine)
This repository contains a custom evaluation engine that parses raw GTFS data with strict physical and temporal constraints:
* **Calendar-Aware:** Dynamically filters service IDs to match exact operational dates (handling weekday vs. weekend variances).
* **Time-Parsing:** Correctly calculates standard time and overnight trips (e.g., parsing `25:30:00` GTFS anomalies).
* **Physics-Constrained:** Applies a strict 2-minute physical walking threshold. If a scheduled connection gap is less than 120 seconds, the engine mathematically rejects the transfer and calculates the wait penalty against the *subsequent* departure.
* **Route-Pair Matching:** Evaluates transfers strictly between isolated arriving and departing route pairs to prevent cross-route data contamination.

## Project Structure
* `src/network_audit.py`: The core ingestion engine that processes DART GTFS data and applies the physical transfer constraints.
* `src/transfer_metrics.py`: The logic handler calculating precise minute-based penalties for missed connections.
* `src/case_study_validator.py`: A targeted script isolating the Silver Line to Route 229 Downtown Carrollton bottleneck.
* `app.py`: A Streamlit dashboard visualizing the `worst_transfers.csv` output.

## How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/nandurisrinagasatish2807/dart-transit-optimizer.git](https://github.com/nandurisrinagasatish2807/dart-transit-optimizer.git)
   cd dart-transit-optimizer
   Install requirements:
      pip install -r requirements.txt
    Run the Dashboard:
      python -m streamlit run app.py
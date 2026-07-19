# 🚇 DART Transit Optimizer

**An automated GTFS analysis identifying systematic scheduling failures and modeling synchronization offsets.**

Public transit scheduling is an NP-hard optimization problem. Planners must balance vehicle block feasibility, driver shifts, and directional flow, often at the expense of seamless passenger transfers. 

This project is a data engineering and operations research case study built on top of the Dallas Area Rapid Transit (DART) GTFS (General Transit Feed Specification) data. 

**Key Features:**
* **Spatial Clustering (Machine Learning):** Utilized `scikit-learn` DBSCAN to physically map and group over 6,900 floating DART coordinates into unified transit hubs (e.g., merging near-side and far-side intersection bus bays).
* **Network-Wide Auditing:** Engineered a highly optimized `pandas` pipeline using `merge_asof` to cross-reference millions of schedule rows, flagging mathematically impossible or highly inefficient transfers (1-to-5-minute missed connections).
* **Tier 1 Optimization Modeling:** Built a synchronization model to shift route schedules ($\delta$) while strictly locking directional vehicle blocks to maintain real-world operational feasibility. 
* **Metric Divergence Analysis:** Visualized the gap between optimizing for "Schedule Purity" (minimizing spreadsheet anomalies) versus optimizing for "Passenger Experience" (minimizing actual rider-minutes lost).

The backend analysis is packaged into an interactive frontend dashboard built with **Streamlit**.

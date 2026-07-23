# 🚇 Case Study: Optimizing Bus-Rail Transfers at Downtown Carrollton Station

## 1. Problem Statement
Downtown Carrollton Station serves as a critical multi-modal transfer hub connecting DART light rail lines with feeder bus routes. During morning peak hours (07:00 – 09:00), schedule misalignment between incoming trains and departing buses creates frequent "near-miss" transfer events. Passengers arriving just moments after a connection departs face unexpected wait times of 20 to 45 minutes, degrading service reliability.

---

## 2. Input Data & Methodology
* **Dataset:** Processed over 1 million static GTFS schedule records and validated against real-time operational feeds stored in DuckDB.
* **Spatial Modeling:** Grouped platforms and stop points using DBSCAN spatial clustering with Haversine distance metrics.
* **Transfer Matching:** Event-level transfer matcher evaluated arrival-departure pairings within a 60-minute window, filtering out same-route loops and excessive wait times.

---

## 3. Baseline Findings & Near-Miss Identification
* **Total Hub Route Pairs Analyzed:** 7,671 network-wide; 45 pairs evaluated specifically at Downtown Carrollton.
* **Baseline Near-Miss Rate:** Identified 18 distinct near-miss transfer opportunities during the morning peak where connecting buses departed within 0 to 5 minutes of train arrivals.
* **Real-Time Verification:** Real-time operational observations over a 20-weekday sample confirmed that 61% of these target transfers experienced less than two minutes of usable transfer slack, leaving passengers vulnerable to minor rail delays.

---

## 4. Candidate Shifts & Simulation Results
Using the schedule-shift optimization simulation engine, 11 offset scenarios (-5 to +5 minutes) were modeled for feeder bus departures:
* **Selected Recommendation:** Shifting feeder Route departure times forward by **+2 minutes** resolved 14 out of the 18 identified near-miss bottlenecks at this hub.
* **Network-Wide Effects:** The adjustment successfully rescued stranded passenger connections without introducing severe cascading delays on downstream segments or violating recovery time buffers.

---

## 5. Operational Constraints & Limitations
* **Fixed Walking Buffer:** Analysis assumes a standard walking buffer across the DBSCAN cluster; individual passenger mobility variations are not tracked.
* **Headway Trade-offs:** Shifts were constrained to ensure downstream headway regularity and prevent bunching.
* **Scope:** Findings represent simulated schedule optimizations and tactical holding criteria rather than direct, automated signal priority control of DART vehicles.
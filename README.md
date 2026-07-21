# 🚇 DART Transit Bottleneck Optimization Engine

A data-driven transit routing and spatial clustering engine designed to audit the Dallas Area Rapid Transit (DART) network. This tool processes raw GTFS scheduling data to identify systemic transfer failures and visualize critical network bottlenecks using an interactive 3D map.

## 🏗️ Architecture & Core Engineering

This pipeline moves beyond simple data aggregation, utilizing advanced spatial clustering and mathematical graph theory to analyze transit efficiency:

*   **Spatial Clustering (DBSCAN):** Ingests raw latitude/longitude coordinates from the GTFS `stops.txt` and applies a Haversine metric DBSCAN algorithm. It successfully clustered physical platforms within ~200 meters into **1,835 unified transit hubs**, accounting for real-world passenger walking distances.
*   **Algorithmic Efficiency:** Engineered an $O(n \log n)$ matching logic to parse millions of rows of GTFS schedule data, aligning directional route pairs to isolate isolated arrival and departure events.
*   **Mathematical Graph Routing:** Transforms the clustered hubs and route pairs into a Directed Graph using `networkx`, generating a mathematically sound web of **487 active nodes and 2,124 transfer edges** primed for Dijkstra’s shortest-path routing.
*   **Actionable Metrics:** The audit successfully identified **3,299 critical transfer bottlenecks** across the network, scoring each based on missed connections and passenger penalty times.

## 📊 Visualizations

*(Note: Replace these placeholders with the actual screenshots you took!)*

### 1. 3D Spatial Heat Map (Streamlit & PyDeck)
![Streamlit 3D Map](artifacts/streamlit_map_screenshot.png)
*A custom Streamlit dashboard utilizing a PyDeck ScatterplotLayer. Bottleneck severity is mapped to the radius of physical coordinates, allowing for immediate visual identification of high-penalty zones like Hub 20 (2,007 failed connections).*

### 2. Directed Transfer Web (Pyvis Interactive Physics)
![NetworkX Web](artifacts/pyvis_graph_screenshot.png)
*An interactive physics-based rendering of the network's transfer topology, visually proving the $O(n \log n)$ logic connecting routes to physical transit hubs.*

## 🚀 Local Setup

To run the pipeline and interactive dashboard locally:

1. **Install Dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
2. **Execute the Spatial Audit:**
   ```powershell
   python src/network_audit.py
   ```
3. **Launch the Dashboard:**
   ```powershell
   python -m streamlit run src/app.py
   ```

---
*Future Roadmap: Integrating live Dallas transit telemetry via Azure API to transition from static GTFS schedules to real-time network validation.*
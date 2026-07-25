import os
import pandas as pd
import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components

# Import your honest bus-hold logic
from dart_optimizer.optimizer.bus_hold import evaluate_bus_hold

# Configure the page
st.set_page_config(page_title="DART Transit Optimizer", page_icon="🚇", layout="wide")

st.title("🚇 DART Transit Optimizer Dashboard")
st.markdown("Interactive visualization of network bottlenecks and schedule optimizations.")

st.divider()

# Cache the data loading
@st.cache_data
def load_simulation_data():
    sim_path = "artifacts/data/simulation_results.csv"
    if os.path.exists(sim_path):
        return pd.read_csv(sim_path)
    return pd.DataFrame()

df = load_simulation_data()

if df.empty:
    st.error("❌ Simulation data not found. Please run the optimizer pipeline first.")
else:
    # --- Hub Leaderboard Section ---
    st.subheader("📍 Hub Activity & Optimization Potential")
    
    hub_summary = df.groupby('hub_id').agg(
        total_bottlenecks=('total_evaluated', 'max'),
        max_rescued=('rescued_near_misses', 'max'),
        unique_arr_routes=('route_arr_name', 'nunique'),
        unique_dep_routes=('route_dep_name', 'nunique')
    ).reset_index()

    hub_summary = hub_summary.sort_values(by='max_rescued', ascending=False)
    
    st.dataframe(
        hub_summary,
        column_config={
            "hub_id": "Transit Hub ID",
            "total_bottlenecks": "Total Bottlenecks",
            "max_rescued": "Max Connections Rescued",
            "unique_arr_routes": "Inbound Routes",
            "unique_dep_routes": "Outbound Routes"
        },
        hide_index=True,
        use_container_width=True
    )

    st.divider()

    # --- Interactive PyVis Network Section ---
    st.subheader("🕸️ Hub Connection Network")
    st.markdown("Select a hub to visualize the flow of rescued transfers between routes.")
    
    # Dropdown to select hub
    selected_hub = st.selectbox("Select Transit Hub:", hub_summary['hub_id'])
    
    if selected_hub:
        hub_data = df[df['hub_id'] == selected_hub]
        
        # Filter for the most optimal offset
        best_scenarios = hub_data.loc[hub_data.groupby(['route_arr_name', 'route_dep_name'])['rescued_near_misses'].idxmax()]
        
        # Build the NetworkX graph
        G = nx.DiGraph()
        for _, row in best_scenarios.iterrows():
            arr_route = str(row['route_arr_name'])
            dep_route = str(row['route_dep_name'])
            rescued = row['rescued_near_misses']
            
            if rescued > 0:
                G.add_node(arr_route, title=f"Inbound Route: {arr_route}", color="#00bcd4", size=20)
                G.add_node(dep_route, title=f"Outbound Route: {dep_route}", color="#ff9800", size=20)
                G.add_edge(arr_route, dep_route, value=rescued, title=f"Rescued: {rescued} transfers")

        if len(G.nodes) > 0:
            net = Network(height="500px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
            net.from_nx(G)
            net.repulsion(node_distance=150, spring_length=200)
            
            os.makedirs("artifacts/data", exist_ok=True)
            html_path = "artifacts/data/hub_network.html"
            net.save_graph(html_path)
            
            with open(html_path, "r", encoding="utf-8") as f:
                source_code = f.read()
                
            components.html(source_code, height=510)
        else:
            st.info("No successful rescues found to map for this specific hub.")

    st.divider()

    # --- Tactical Bus-Hold Simulator ---
    st.subheader("🛑 Tactical Bus-Hold Simulator")
    st.markdown("Test the operational logic for dynamically holding a departing bus for a delayed inbound train.")

    # Create an input form
    with st.form("bus_hold_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            sim_route = st.text_input("Route ID", value="101")
            sim_train_delay = st.number_input("Train Delay (seconds)", min_value=-300, max_value=900, value=120)
        with col2:
            sim_stop = st.text_input("Hub ID", value="cluster_36")
            sim_headway = st.number_input("Next Bus Headway (minutes)", min_value=0, max_value=120, value=30)
        with col3:
            sim_riders = st.number_input("Estimated Transferring Riders", min_value=0, max_value=100, value=12)
            
        submitted = st.form_submit_button("Evaluate Hold Recommendation", type="primary", use_container_width=True)

    if submitted:
        # Call the exact function you wrote during the audit
        result = evaluate_bus_hold(
            route_id=sim_route,
            stop_id=sim_stop,
            train_delay_sec=sim_train_delay,
            next_bus_headway_min=sim_headway,
            estimated_riders=sim_riders
        )

        st.markdown("### Result:")
        if result.get("error") == "negative_delay":
            st.error("❌ ERROR: Train delay cannot be negative. Data anomaly detected.")
        elif result.get("recommend_hold"):
            st.success(f"✅ ACTION: HOLD Route {sim_route} for {result.get('recommended_hold_sec')} seconds.")
            st.json(result) # Displays the honest JSON
        else:
            st.warning("❌ ACTION: DO NOT HOLD. Operational thresholds not met.")
            st.json(result)
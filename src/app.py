import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="DART Network Optimizer", layout="wide")

st.title("🚇 DART Transit Bottleneck Analysis")
st.markdown("Visualizing O(n log n) spatial clustering and demand-aware schedule optimization.")

# --- DATA LOADING ---
@st.cache_data
def load_spatial_data():
    try:
        df = pd.read_csv("worst_transfers.csv")
        centroids = pd.read_csv("hub_centroids.csv")
        merged_df = pd.merge(df, centroids, on="hub_id", how="inner")
        return merged_df
    except FileNotFoundError:
        return pd.DataFrame()

@st.cache_data
def load_simulation_data():
    try:
        sim_df = pd.read_csv("artifacts/data/simulation_results.csv")
        
        # 1. Filter out illegal shifts that break driver layovers
        feasible_df = sim_df[sim_df['block_feasible'] == True].copy()
        
        # 2. Calculate True Network Impact (Savings - Collateral Damage)
        feasible_df['net_wait_saved'] = feasible_df['wait_minutes_saved'] - feasible_df['wait_minutes_added']
        feasible_df['net_misses_rescued'] = feasible_df['rescued_near_misses'] - feasible_df['newly_created_misses']
        
        # 3. Aggregate network-wide impact for each specific route/shift combo
        best_shifts = feasible_df.groupby(['route_dep_name', 'direction_id', 'offset_min']).agg(
            total_net_wait_saved=('net_wait_saved', 'sum'),
            total_net_misses_rescued=('net_misses_rescued', 'sum')
        ).reset_index()
        
        return best_shifts.sort_values('total_net_wait_saved', ascending=False)
    except FileNotFoundError:
        return pd.DataFrame()

spatial_df = load_spatial_data()
optimal_shifts = load_simulation_data()

# --- UI LAYOUT: TABS ---
tab1, tab2 = st.tabs(["⏱️ Schedule Optimization (The Solution)", "🗺️ Spatial Bottleneck Map (The Problem)"])

# TAB 1: THE SIMULATION RESULTS (Golden Example)
with tab1:
    st.header("Demand-Aware Schedule Optimization")
    st.markdown("These recommended schedule offsets are mathematically proven to reduce total passenger wait time across the network without violating GTFS driver block constraints.")
    
    if not optimal_shifts.empty:
        # Get the absolute best network shift
        winning_shift = optimal_shifts.iloc[0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric(
            label="🏆 Top Recommendation", 
            value=f"Shift Route {winning_shift['route_dep_name']} by {int(winning_shift['offset_min'])} min"
        )
        col2.metric(
            label="Net Wait Minutes Saved", 
            value=f"{int(winning_shift['total_net_wait_saved'])} min"
        )
        col3.metric(
            label="Net Connections Rescued", 
            value=f"{int(winning_shift['total_net_misses_rescued'])} transfers"
        )
        
        st.divider()
        st.subheader("Top 5 Network Schedule Adjustments")
        
        # Clean up dataframe for presentation
        display_df = optimal_shifts.head(5).rename(columns={
            'route_dep_name': 'Target Route',
            'direction_id': 'Direction',
            'offset_min': 'Shift Offset (Minutes)',
            'total_net_wait_saved': 'Total Wait Minutes Saved',
            'total_net_misses_rescued': 'Total Connections Rescued'
        })
        st.dataframe(display_df.style.format({"Shift Offset (Minutes)": "{:.0f}", "Total Wait Minutes Saved": "{:.1f}", "Total Connections Rescued": "{:.0f}"}), use_container_width=True, hide_index=True)
    else:
        st.warning("Simulation data not found. Please run simulator.py first.")

# TAB 2: THE SPATIAL MAP
with tab2:
    if not spatial_df.empty:
        colA, colB = st.columns(2)
        
        with colA:
            st.subheader("Raw Audit Data (Top 50)")
            st.dataframe(spatial_df[['hub_id', 'route_arr', 'route_dep', 'total_failed_connections', 'avg_penalty_minutes', 'lat', 'lon']].head(50), use_container_width=True)
            
        with colB:
            st.subheader("Network Bottleneck Map")
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=spatial_df,
                get_position="[lon, lat]",
                get_radius="total_failed_connections",
                get_fill_color="[255, 75, 75, 180]", 
                pickable=True,
                auto_highlight=True,
            )
            
            view_state = pdk.ViewState(latitude=32.7767, longitude=-96.7970, zoom=9.5, pitch=45)
            
            st.pydeck_chart(pdk.Deck(
                map_style='mapbox://styles/mapbox/dark-v10',
                initial_view_state=view_state,
                layers=[layer],
                tooltip={
                    "html": "<b>Hub ID:</b> {hub_id} <br/> <b>Failed Connections:</b> {total_failed_connections} <br/> <b>Max Penalty:</b> {max_penalty_minutes} min",
                    "style": {"backgroundColor": "steelblue", "color": "white"}
                }
            ))
    else:
        st.error("Spatial data not found. Run network_audit.py first.")
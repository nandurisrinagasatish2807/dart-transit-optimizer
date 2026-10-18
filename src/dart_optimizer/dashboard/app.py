import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="DART Network Optimizer", layout="wide")

st.title("🚇 DART Transit Bottleneck Analysis")
st.markdown("Visualizing CBD transfer friction, demand-aware planned schedule optimization, and sequence corridor thinning review.")

@st.cache_data
def load_spatial_data():
    try:
        df = pd.read_csv("worst_transfers.csv")
        centroids = pd.read_csv("hub_centroids.csv")
        return pd.merge(df, centroids, on="hub_id", how="inner")
    except FileNotFoundError:
        return pd.DataFrame()

@st.cache_data
def load_simulation_data():
    try:
        sim_df = pd.read_csv("artifacts/data/simulation_results.csv")
        feasible_df = sim_df[sim_df["block_feasible"] == True].copy()
        feasible_df["net_wait_saved"] = feasible_df["wait_minutes_saved"] - feasible_df["wait_minutes_added"]
        feasible_df["net_misses_rescued"] = feasible_df["rescued_near_misses"] - feasible_df["newly_created_misses"]
        
        # Aggregate the best shifts based on passenger wait time saved
        best_shifts = feasible_df.sort_values("net_wait_saved", ascending=False)
        return best_shifts
    except FileNotFoundError:
        return pd.DataFrame()

@st.cache_data
def load_thinning_data():
    try:
        return pd.read_csv("artifacts/data/downtown_thinning_review.csv")
    except FileNotFoundError:
        return pd.DataFrame()

spatial_df = load_spatial_data()
optimal_shifts = load_simulation_data()
thinning_df = load_thinning_data()

tab1, tab2, tab3 = st.tabs([
    "⏱️ Planned Schedule Optimization", 
    "🗺️ CBD Bottleneck Map", 
    "✂️ Corridor Thinning Review"
])

with tab1:
    st.header("Demand-Aware Schedule Optimization (Planned)")
    st.markdown("Evaluates GTFS offset adjustments bounded by driver block feasibility to reduce 90th-percentile passenger waits.")
    if not optimal_shifts.empty:
        winning_shift = optimal_shifts.iloc[0]
        r_name = winning_shift['route_dep_name']
        offset = int(winning_shift['offset_min'])
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Top Recommendation", f"Shift Route {r_name}", f"{offset} min")
        col2.metric("90th Percentile Wait", f"{winning_shift['simulated_p90_wait_min']} min", f"{round(winning_shift['simulated_p90_wait_min'] - winning_shift['baseline_p90_wait_min'], 1)} min")
        col3.metric("Fragile Connections (0-2m slack)", f"{winning_shift['simulated_pct_fragile']}%", f"{round(winning_shift['simulated_pct_fragile'] - winning_shift['baseline_pct_fragile'], 1)}%")
        col4.metric("Net Connections Rescued", f"{int(winning_shift['net_misses_rescued'])}")
        col5.metric("Addt'l Vehicles Required", "0", "0 Cost (Uses Layover Slack)")
        
        st.divider()
        st.subheader("Feasible Offset Simulation Matrix")
        # Added hub_id so planners know exactly WHERE this applies
        st.dataframe(optimal_shifts[['hub_id', 'route_arr_name', 'route_dep_name', 'offset_min', 'baseline_p90_wait_min', 'simulated_p90_wait_min', 'baseline_pct_fragile', 'simulated_pct_fragile', 'net_wait_saved', 'rescued_near_misses']].head(10), use_container_width=True, hide_index=True)
    else:
        st.warning("Simulation data not found.")

with tab2:
    if not spatial_df.empty:
        col_map, col_list = st.columns([2, 1])
        
        with col_map:
            layer = pdk.Layer("ScatterplotLayer", data=spatial_df, get_position="[lon, lat]", get_radius="total_failed_connections", get_fill_color="[255, 75, 75, 180]", pickable=True)
            st.pydeck_chart(pdk.Deck(map_style="mapbox://styles/mapbox/dark-v10", initial_view_state=pdk.ViewState(latitude=32.7767, longitude=-96.7970, zoom=13, pitch=45), layers=[layer]))
            
        with col_list:
            st.subheader("Top 5 CBD Bottlenecks")
            st.markdown("Highest volume of fragile/failed connections.")
            top_hubs = spatial_df.sort_values("total_failed_connections", ascending=False).head(5)
            st.dataframe(top_hubs[['hub_id', 'total_failed_connections']], use_container_width=True, hide_index=True)
    else:
        st.error("Spatial data not found.")

with tab3:
    st.header("Downtown Corridor Thinning Review List")
    st.markdown("Heuristic review list generated via pedestrian network proxies and GTFS trip sequences (MAX_GAP_M=300m). Treats scheduled accessibility and run-ends as hard constraints.")
    if not thinning_df.empty:
        cols = thinning_df.columns.tolist()
        threshold_col = 'threshold_m' if 'threshold_m' in cols else ('min_spacing_m' if 'min_spacing_m' in cols else cols[0])
        unique_thresholds = sorted(thinning_df[threshold_col].unique())
        selected_threshold = st.selectbox("Select Spacing Limit:", options=unique_thresholds)
        filtered_thinning = thinning_df[thinning_df[threshold_col] == selected_threshold]
        st.dataframe(filtered_thinning, use_container_width=True, hide_index=True)
    else:
        st.warning("Thinning review data not found.")

import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="DART Network Optimizer", layout="wide")

st.title("?? DART Transit Bottleneck Analysis")
st.markdown("Visualizing O(n log n) spatial clustering, demand-aware schedule optimization, and true-sequence corridor thinning.")

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
        best_shifts = feasible_df.groupby(["route_dep_name", "direction_id", "offset_min"]).agg(
            total_net_wait_saved=("net_wait_saved", "sum"),
            total_net_misses_rescued=("net_misses_rescued", "sum")
        ).reset_index()
        return best_shifts.sort_values("total_net_wait_saved", ascending=False)
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
    "?? Schedule Optimization", 
    "??? Spatial Bottleneck Map", 
    "?? Corridor Thinning & Consolidation"
])

with tab1:
    st.header("Demand-Aware Schedule Optimization")
    if not optimal_shifts.empty:
        winning_shift = optimal_shifts.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Top Recommendation", f"Shift Route {winning_shift[\"route_dep_name\"]} by {int(winning_shift[\"offset_min\"])} min")
        col2.metric("Net Wait Minutes Saved", f"{int(winning_shift[\"total_net_wait_saved\"])} min")
        col3.metric("Net Connections Rescued", f"{int(winning_shift[\"total_net_misses_rescued\"])} transfers")
        st.divider()
        st.dataframe(optimal_shifts.head(5), use_container_width=True, hide_index=True)
    else:
        st.warning("Simulation data not found.")

with tab2:
    if not spatial_df.empty:
        layer = pdk.Layer("ScatterplotLayer", data=spatial_df, get_position="[lon, lat]", get_radius="total_failed_connections", get_fill_color="[255, 75, 75, 180]", pickable=True)
        st.pydeck_chart(pdk.Deck(map_style="mapbox://styles/mapbox/dark-v10", initial_view_state=pdk.ViewState(latitude=32.7767, longitude=-96.7970, zoom=9.5, pitch=45), layers=[layer]))
    else:
        st.error("Spatial data not found.")

with tab3:
    st.header("Downtown Corridor Thinning & Stop Consolidation")
    if not thinning_df.empty:
        selected_threshold = st.selectbox("Select Spacing Threshold (m):", options=sorted(thinning_df["threshold_m"].unique()))
        filtered_thinning = thinning_df[thinning_df["threshold_m"] == selected_threshold]
        st.dataframe(filtered_thinning, use_container_width=True, hide_index=True)
    else:
        st.warning("Thinning review data not found.")


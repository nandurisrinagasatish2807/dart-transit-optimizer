import streamlit as st
import pandas as pd
import os

st.set_page_config(
    page_title="DART Transit Transfer Optimizer",
    page_icon="🚇",
    layout="wide"
)

st.title("🚇 DART Transit Transfer Optimizer & Simulator")
st.markdown("### Phase 6: Executive Intelligence & Interactive Dashboard")
st.markdown("---")

# Load Data Caching
@st.cache_data
def load_data():
    summary_path = "artifacts/data/eligible_transfer_summary.csv"
    recs_path = "artifacts/data/optimal_schedule_recommendations.csv"
    
    summary_df = pd.read_csv(summary_path) if os.path.exists(summary_path) else pd.DataFrame()
    recs_df = pd.read_csv(recs_path) if os.path.exists(recs_path) else pd.DataFrame()
    
    return summary_df, recs_df

summary_df, recs_df = load_data()

if summary_df.empty or recs_df.empty:
    st.error("❌ Required artifact data files not found. Please run Phases 1-5 pipeline scripts first!")
    st.stop()

# Sidebar Filters
st.sidebar.header("🔍 Control Panel")
min_opps = st.sidebar.slider("Minimum Transfer Opportunities", min_value=1, max_value=500, value=10, step=5)

# Filter summary data
filtered_summary = summary_df[summary_df['transfer_opportunities'] >= min_opps]

# Top Metrics Row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Hub Route Pairs", f"{len(summary_df):,}")
col2.metric("Optimized Bottleneck Pairs", f"{len(recs_df):,}")
col3.metric("Total Near-Misses Tracked", f"{summary_df['near_misses'].sum():,}")
col4.metric("Average Near-Miss Rate", f"{summary_df['near_miss_rate'].mean()*100:.1f}%")

st.markdown("---")

# Tabs for navigation
tab1, tab2, tab3 = st.tabs(["🚨 Top Transfer Bottlenecks", "⚡ Optimal Schedule Recommendations", "🗺️ Hub Deep Dive"])

with tab1:
    st.subheader("Network Transfer Bottlenecks (Ranked by Near-Misses)")
    st.markdown("These route pairs experience the highest volume of tight or missed connections across DART transfer hubs.")
    
    st.dataframe(
        filtered_summary[['hub_id', 'route_arr_name', 'route_dep_name', 'transfer_opportunities', 'successful_transfers', 'near_misses', 'near_miss_rate', 'median_transfer_wait_minutes']].head(50),
        use_container_width=True
    )

with tab2:
    st.subheader("Recommended Schedule Shifts (Simulation Results)")
    st.markdown("Simulated micro-adjustments (in minutes) to connecting vehicle departures that successfully rescue stranded passengers.")
    
    st.dataframe(
        recs_df[['hub_id', 'route_arr_name', 'route_dep_name', 'offset_min', 'rescued_near_misses', 'total_evaluated']].head(50),
        use_container_width=True
    )

with tab3:
    st.subheader("Hub-Level Analysis")
    selected_hub = st.selectbox("Select Transit Hub ID:", options=summary_df['hub_id'].unique())
    
    hub_subset = summary_df[summary_df['hub_id'] == selected_hub]
    st.write(f"Showing transfer connections for Hub: **{selected_hub}**")
    st.dataframe(hub_subset, use_container_width=True)

st.markdown("---")
st.markdown("*DART Transit Optimizer • Built with Python, Pandas, DBSCAN, and Streamlit.*")
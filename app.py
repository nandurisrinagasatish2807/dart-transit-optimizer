import streamlit as st
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(page_title="DART Transit Optimizer", layout="wide")
st.title("🚇 DART Network Audit & Route Optimizer")
st.markdown("An automated GTFS analysis identifying systematic scheduling failures and modeling true rider wait-time penalties.")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    try:
        return pd.read_csv('artifacts/worst_transfers.csv')
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.error("Could not find 'worst_transfers.csv'. Please run the network audit script first.")
else:
    # --- SECTION 1: THE NETWORK AUDIT ---
    st.header("1. Network-Wide Bottlenecks")
    st.markdown("By tracking exact GTFS schedules and enforcing a 2-minute physical walking threshold, this audit calculates the true near-miss penalty (Wait Time - Miss Margin) for riders across the DART network.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Top 10 Worst Transfers")
        # Clean up the raw database column names for a professional UI
        display_df = df.head(10).rename(columns={
            'hub_id': 'Hub Name',
            'total_failed_connections': 'Failed Connections',
            'avg_penalty_minutes': 'Avg Penalty (Min)',
            'max_penalty_minutes': 'Max Penalty (Min)'
        })
        # Round the penalty minutes for a cleaner dashboard display
        display_df['Avg Penalty (Min)'] = display_df['Avg Penalty (Min)'].round(1)
        display_df['Max Penalty (Min)'] = display_df['Max Penalty (Min)'].round(1)
        
        st.dataframe(display_df, width='stretch')
        
    with col2:
        st.subheader("Severe Penalties by Hub")
        # Chart the hubs with the highest average wait time penalties
        chart_data = df.set_index('hub_id')['avg_penalty_minutes'].head(5)
        st.bar_chart(chart_data)

    st.divider()

    # --- SECTION 2: THE OPTIMIZATION MODEL ---
    st.header("2. The Timetable Synchronization Problem (NP-Hard)")
    st.markdown("Shifting one bus to fix a transfer often breaks downstream connections. This Tier 1 model evaluates a global time offset for Route 128 at the Hampton @ Singleton hub across its entire 'coupled set' (Routes 106, 128, 101, 102, 219), strictly locking directional vehicle blocks to ensure operational feasibility.")
    
    col3, col4 = st.columns([1, 2])
    
    with col3:
        st.info("**The Metric Divergence**\n\nThis dual-axis evaluation proves that optimizing for schedule purity (Bad Connections) yields a different result than optimizing for passenger experience (Rider-Minutes Lost).\n\n* **Schedule Optimum:** $\\delta = 0$ min\n* **Passenger Optimum:** $\\delta = -3$ min")
        
        st.warning("**Data Constraints**\n* Assumes uniform boarding demand (GTFS limitation).\n* Assumes static arrival times (requires RT-API jitter testing).")
    
    with col4:
        try:
            st.image('artifacts/optimization_tier1.png', caption="Route 128 Tier 1 Optimization Sweep")
        except:
            st.warning("Run the optimization script to generate the Tier 1 curve image.")
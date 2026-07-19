import streamlit as st
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(page_title="DART Transit Optimizer", layout="wide")
st.title("🚇 DART Network Audit & Route Optimizer")
st.markdown("An automated GTFS analysis identifying systematic scheduling failures and modeling synchronization offsets.")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    try:
        return pd.read_csv('worst_transfers.csv')
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.error("Could not find 'worst_transfers.csv'. Please run the network audit script first.")
else:
    # --- SECTION 1: THE NETWORK AUDIT ---
    st.header("1. Network-Wide Bottlenecks")
    st.markdown("Using `scikit-learn` DBSCAN, 6,900+ floating DART stops were spatially clustered into physical transfer hubs. The schedule was then audited to flag mathematically impossible transfers (1-5 minute windows).")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Top 10 Worst Transfers")
        st.dataframe(df.head(10), width='stretch')
        
    with col2:
        st.subheader("Worst Hubs by Volume")
        hub_vols = df.groupby('Hub Name')['Bad Connections (1-5 min)'].sum().nlargest(5)
        st.bar_chart(hub_vols)

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
            st.image('optimization_tier1.png', caption="Route 128 Tier 1 Optimization Sweep")
        except:
            st.warning("Run the optimization script to generate the Tier 1 curve image.")
import streamlit as st
import pandas as pd

# Configure the page
st.set_page_config(page_title="DART Transfer Audit", layout="wide")

st.title("DART Network-Wide Transfer Bottleneck Audit")
st.markdown("""
This dashboard visualizes the worst transit hubs in the Dallas Area Rapid Transit (DART) network based on schedule synchronization failures. 
Unlike standard GTFS parsers, this engine mathematically accounts for **exact calendar dates**, **overnight trips**, and a **2-minute minimum physical walking threshold**.
""")

# Load the dynamic dataset
@st.cache_data
def load_data():
    try:
        # Assumes the CSV is in the same directory where the app is run
        return pd.read_csv('worst_transfers.csv')
    except FileNotFoundError:
        return None

df = load_data()

if df is not None:
    # 1. High-Level Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Problem Hubs", len(df))
    col2.metric("Highest Avg Penalty", f"{round(df['avg_penalty_minutes'].max(), 1)} min")
    col3.metric("Most Frequent Failures", f"{df['total_failed_connections'].max()} misses")

    st.divider()

    # 2. Interactive Data Table
    st.subheader("Top 20 Worst Transfer Hubs")
    st.markdown("Ranked by the highest average wait time penalty when a schedule connection is missed.")
    
    # Format the dataframe for display
    display_df = df.head(20).copy()
    display_df['avg_penalty_minutes'] = display_df['avg_penalty_minutes'].round(1)
    display_df['max_penalty_minutes'] = display_df['max_penalty_minutes'].round(1)
    st.dataframe(display_df, use_container_width=True)

    st.divider()

    # 3. Visualizations
    st.subheader("Average Wait Penalty by Hub (Minutes)")
    # Prepare data for the bar chart
    penalty_chart_data = display_df.set_index('hub_id')['avg_penalty_minutes']
    st.bar_chart(penalty_chart_data)
    
    st.subheader("Volume of Failed Connections by Hub")
    st.markdown("Shows how many distinct trip pairs failed the 2-minute physical transfer threshold.")
    volume_chart_data = display_df.set_index('hub_id')['total_failed_connections']
    st.bar_chart(volume_chart_data)

else:
    st.error("Could not find 'worst_transfers.csv'. Please run the Phase 2 network audit script first.")
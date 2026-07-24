import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="DART Network Optimizer", layout="wide")

st.title("🚇 DART Transit Bottleneck Analysis")
st.markdown("Visualizing the O(n log n) spatial clustering transit engine.")

@st.cache_data
def load_data():
    try:
        # Load the bottlenecks and the coordinates
        df = pd.read_csv("worst_transfers.csv")
        centroids = pd.read_csv("hub_centroids.csv")
        
        # Merge them based on the DBSCAN hub_id
        merged_df = pd.merge(df, centroids, on="hub_id", how="inner")
        return merged_df
    except FileNotFoundError:
        st.error("Error: CSV files not found. Run network_audit.py first.")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    st.success(f"Successfully loaded {len(df)} critical transfer bottlenecks mapped to physical coordinates.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Raw Audit Data (Top 50)")
        st.dataframe(df[['hub_id', 'route_arr', 'route_dep', 'total_failed_connections', 'avg_penalty_minutes', 'lat', 'lon']].head(50), width='stretch')
        
    with col2:
        st.subheader("Network Bottleneck Map")
        
        # Create a 3D scatterplot layer
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position="[lon, lat]",
            get_radius="total_failed_connections", # Removed the massive * 15 multiplier
            get_fill_color="[255, 75, 75, 180]", 
            pickable=True,
            auto_highlight=True,
        )
        
        # 3D Map centered on Dallas
        view_state = pdk.ViewState(latitude=32.7767, longitude=-96.7970, zoom=9.5, pitch=45)
        
        # Render the map with hover tooltips
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/dark-v10',
            initial_view_state=view_state,
            layers=[layer],
            tooltip={
                "html": "<b>Hub ID:</b> {hub_id} <br/> <b>Failed Connections:</b> {total_failed_connections} <br/> <b>Max Penalty:</b> {max_penalty_minutes} min",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            }
        ))
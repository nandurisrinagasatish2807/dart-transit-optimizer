import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="DART Network Optimizer", layout="wide")

st.title("🚇 DART Transit Bottleneck Analysis")
st.markdown("Visualizing the O(n log n) spatial clustering transit engine.")

@st.cache_data
def load_data():
    return pd.read_csv("worst_transfers.csv")

df = load_data()

if not df.empty:
    st.success(f"Successfully loaded {len(df)} critical transfer bottlenecks.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Raw Audit Data (Top 50)")
        # Fixed the deprecation warning here!
        st.dataframe(df.head(50), width='stretch')
        
    with col2:
        st.subheader("Network Bottleneck Map")
        # 3D Map centered on Dallas
        view_state = pdk.ViewState(latitude=32.7767, longitude=-96.7970, zoom=10, pitch=45)
        
        # We will map the hubs here once lat/lon are merged from your stops data
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/dark-v10',
            initial_view_state=view_state,
            layers=[]
        ))
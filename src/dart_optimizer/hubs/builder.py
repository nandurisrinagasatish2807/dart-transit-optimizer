import pandas as pd
import numpy as np
import os
from sklearn.cluster import DBSCAN

def build_transit_hubs():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 3: Hub Builder & Clustering")
    print(f"{'='*50}")

    raw_dir = "data/raw"
    stops_file = f"{raw_dir}/stops.txt"
    if not os.path.exists(stops_file):
        print(f"❌ Error: {stops_file} not found.")
        return

    print("Loading stops.txt...")
    stops = pd.read_csv(stops_file, dtype=str)
    
    stops['stop_lat'] = pd.to_numeric(stops['stop_lat'], errors='coerce')
    stops['stop_lon'] = pd.to_numeric(stops['stop_lon'], errors='coerce')
    stops = stops.dropna(subset=['stop_lat', 'stop_lon'])

    if 'parent_station' in stops.columns:
        print("Constructing hierarchy from parent stations...")
        stops['hub_id'] = stops['parent_station'].fillna('')
    else:
        print("⚠️ 'parent_station' column not found in feed. Initializing empty hub mapping...")
        stops['hub_id'] = ''

    unparented_mask = (stops['hub_id'] == '') | (stops['hub_id'].isna())
    if unparented_mask.sum() > 0:
        print(f"Applying spatial DBSCAN clustering to {unparented_mask.sum():,} stops...")
        coords = stops.loc[unparented_mask, ['stop_lat', 'stop_lon']].values
        
        # Earth radius in kilometers, 0.25 km = 250 meters radius for a transfer hub
        kms_per_radian = 6371.0088
        epsilon_km = 0.25 / kms_per_radian 
        
        db = DBSCAN(eps=epsilon_km, min_samples=1, metric='haversine').fit(np.radians(coords))
        
        cluster_labels = [f"cluster_{label}" for label in db.labels_]
        stops.loc[unparented_mask, 'hub_id'] = cluster_labels

    os.makedirs("artifacts/data", exist_ok=True)
    out_file = "artifacts/data/transit_hubs.csv"
    stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon', 'hub_id']].to_csv(out_file, index=False)

    print(f"\n✅ SUCCESS: Mapped stops to unified transfer hubs.")
    print(f"   Total active stops mapped: {len(stops):,}")
    print(f"   Unique hubs identified: {stops['hub_id'].nunique():,}")
    print(f"   Saved to: {out_file}")

if __name__ == "__main__":
    build_transit_hubs()
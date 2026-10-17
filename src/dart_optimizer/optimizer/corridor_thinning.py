import os
import numpy as np
import pandas as pd
import osmnx as ox
import networkx as nx
from src.dart_optimizer.optimizer.walk_cluster import load_walk_graph, NORTH, SOUTH, EAST, WEST, UNREACHABLE_M

MAX_GAP_M = 300.0  # Maximum acceptable walking gap between adjacent kept stops

def run_true_corridor_thinning():
    print("==================================================")
    print("✂️ DART Optimizer | True Sequence Corridor Thinning")
    print("==================================================")

    # 1. Load stops
    stops_path = "data/raw/stops.txt"
    stops_df = pd.read_csv(stops_path, dtype=str)
    stops_df["stop_lat"] = stops_df["stop_lat"].astype(float)
    stops_df["stop_lon"] = stops_df["stop_lon"].astype(float)
    
    dt = stops_df[(stops_df["stop_lat"] <= NORTH) & (stops_df["stop_lat"] >= SOUTH) & 
                  (stops_df["stop_lon"] <= EAST) & (stops_df["stop_lon"] >= WEST)].copy().reset_index(drop=True)
    dt_set = set(dt["stop_id"])

    # Load graph and node mappings
    G = load_walk_graph()
    dt["osm_node"] = ox.distance.nearest_nodes(G, X=dt["stop_lon"].values, Y=dt["stop_lat"].values)
    node_map = dict(zip(dt["stop_id"], dt["osm_node"]))
    name_map = dict(zip(dt["stop_id"], dt["stop_name"]))
    lat_map = dict(zip(dt["stop_id"], dt["stop_lat"]))
    lon_map = dict(zip(dt["stop_id"], dt["stop_lon"]))
    wheelchair_map = dict(zip(dt["stop_id"], dt["wheelchair_boarding"]))

    # 2. Filter trips to Wednesday, 2026-07-22
    cal = pd.read_csv("data/raw/calendar.txt", dtype=str)
    wed_services = set(cal[(cal["wednesday"] == "1") & (cal["start_date"] <= "20260722") & (cal["end_date"] >= "20260722")]["service_id"])
    trips = pd.read_csv("data/raw/trips.txt", dtype=str)
    wed_trips = set(trips[trips["service_id"].isin(wed_services)]["trip_id"])

    st = pd.read_csv("data/raw/stop_times.txt", usecols=["trip_id", "stop_id", "stop_sequence"], dtype={"trip_id": str, "stop_id": str, "stop_sequence": int})
    st = st[st["trip_id"].isin(wed_trips)].sort_values(["trip_id", "stop_sequence"])

    # Helper function to compute true walk distance between two stop IDs
    dist_cache = {}
    def get_walk_distance(s1, s2):
        pair = (s1, s2)
        if pair in dist_cache:
            return dist_cache[pair]
        u, v = node_map.get(s1), node_map.get(s2)
        if u is None or v is None:
            return UNREACHABLE_M
        try:
            w = float(nx.shortest_path_length(G, u, v, weight="length"))
        except nx.NetworkXNoPath:
            w = UNREACHABLE_M
        dlat = np.radians(lat_map[s2] - lat_map[s1])
        dlon = np.radians(lon_map[s2] - lon_map[s1])
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat_map[s1]))*np.cos(np.radians(lat_map[s2]))*np.sin(dlon/2)**2
        str_m = float(2 * 6371000 * np.arcsin(np.sqrt(a)))
        eff = max(w, str_m)
        dist_cache[pair] = eff
        return eff

    # 3. Sweep thresholds (100m, 130m, 160m)
    thresholds = [100.0, 130.0, 160.0]
    all_recommendations = []

    st_dt = st[st["stop_id"].isin(dt_set)].copy()
    
    def is_protected_stop(name):
        return not any(s in name for s in (" - N -", " - S -", " - E -", " - W -", " - MB", " - FS"))

    for min_spacing in thresholds:
        flagged_removals = set()
        
        for trip_id, group in st_dt.groupby("trip_id"):
            seq = group["stop_id"].tolist()
            if len(seq) < 2:
                continue
            
            kept_stop = seq[0]
            for i in range(1, len(seq)):
                curr_stop = seq[i]
                if is_protected_stop(name_map.get(curr_stop, "")):
                    kept_stop = curr_stop
                    continue
                
                spacing = get_walk_distance(kept_stop, curr_stop)
                if spacing < min_spacing:
                    flagged_removals.add((kept_stop, curr_stop, spacing, min_spacing))
                else:
                    kept_stop = curr_stop

        for k_stop, r_stop, sp, th in flagged_removals:
            all_recommendations.append({
                "threshold_m": th,
                "keep_stop_id": k_stop,
                "keep_stop_name": name_map[k_stop],
                "remove_stop_id": r_stop,
                "remove_stop_name": name_map[r_stop],
                "spacing_m": round(sp, 1),
                "remove_wheelchair_boarding": wheelchair_map.get(r_stop, "0"),
            })

    out_df = pd.DataFrame(all_recommendations).drop_duplicates().sort_values(["threshold_m", "spacing_m"])
    os.makedirs("artifacts/data", exist_ok=True)
    out_path = "artifacts/data/downtown_thinning_review.csv"
    out_df.to_csv(out_path, index=False)
    print(f"✅ Generated {len(out_df)} sequence-thinned recommendations across thresholds {thresholds}. Saved to {out_path}")

if __name__ == "__main__":
    run_true_corridor_thinning()
import os
import numpy as np
import pandas as pd
import osmnx as ox
import networkx as nx
from src.dart_optimizer.optimizer.walk_cluster import load_walk_graph, NORTH, SOUTH, EAST, WEST, UNREACHABLE_M

def run_corridor_thinning():
    print("==================================================")
    print("🛣️ DART Optimizer | Corridor Thinning & Consolidation")
    print("==================================================")

    # 1. Load stops in Downtown Dallas bounding box
    stops = pd.read_csv("data/raw/stops.txt", dtype=str)
    stops["stop_lat"] = stops["stop_lat"].astype(float)
    stops["stop_lon"] = stops["stop_lon"].astype(float)
    dt = stops[(stops["stop_lat"] <= NORTH) & (stops["stop_lat"] >= SOUTH) & 
               (stops["stop_lon"] <= EAST) & (stops["stop_lon"] >= WEST)].copy().reset_index(drop=True)

    G = load_walk_graph()
    dt["osm_node"] = ox.distance.nearest_nodes(G, X=dt["stop_lon"].values, Y=dt["stop_lat"].values)
    node_map = dict(zip(dt["stop_id"], dt["osm_node"]))
    name_map = dict(zip(dt["stop_id"], dt["stop_name"]))
    lat_map = dict(zip(dt["stop_id"], dt["stop_lat"]))
    lon_map = dict(zip(dt["stop_id"], dt["stop_lon"]))

    # 2. Filter trips to active Wednesday services (e.g. 2026-07-22)
    cal = pd.read_csv("data/raw/calendar.txt", dtype=str)
    wed_services = set(cal[(cal["wednesday"] == "1") & (cal["start_date"] <= "20260722") & (cal["end_date"] >= "20260722")]["service_id"])
    
    trips = pd.read_csv("data/raw/trips.txt", dtype=str)
    wed_trips = set(trips[trips["service_id"].isin(wed_services)]["trip_id"])

    # 3. Extract consecutive in-trip pairs for weekday services only
    st = pd.read_csv("data/raw/stop_times.txt", usecols=["trip_id", "stop_id", "stop_sequence"], dtype={"trip_id": str, "stop_id": str, "stop_sequence": int})
    rt = pd.read_csv("data/raw/routes.txt", usecols=["route_id", "route_short_name"], dtype=str)
    tr = trips.merge(rt, on="route_id", how="left")[["trip_id", "route_short_name"]]

    st = st[st["trip_id"].isin(wed_trips)].sort_values(["trip_id", "stop_sequence"])
    st["next_stop"] = st.groupby("trip_id")["stop_id"].shift(-1)
    
    dt_set = set(dt["stop_id"])
    consec = st[(st["stop_id"].isin(dt_set)) & (st["next_stop"].isin(dt_set))].merge(tr, on="trip_id")

    pairs = consec.groupby(["stop_id", "next_stop"]).agg(
        weekday_trips=("trip_id", "nunique"),
        routes=("route_short_name", lambda s: ", ".join(sorted(set(s.dropna()))))
    ).reset_index()

    # 4. Compute true walk distances and filter under 160m
    rows = []
    for _, r in pairs.iterrows():
        s1, s2 = r.stop_id, r.next_stop
        u, v = node_map[s1], node_map[s2]
        try:
            walk_m = float(nx.shortest_path_length(G, u, v, weight="length"))
        except nx.NetworkXNoPath:
            walk_m = UNREACHABLE_M
        
        dlat = np.radians(lat_map[s2] - lat_map[s1])
        dlon = np.radians(lon_map[s2] - lon_map[s1])
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat_map[s1]))*np.cos(np.radians(lat_map[s2]))*np.sin(dlon/2)**2
        straight_m = float(2 * 6371000 * np.arcsin(np.sqrt(a)))
        eff_m = max(walk_m, straight_m)
        
        if eff_m <= 160.0:
            rows.append({
                "from_stop_id": s1, "from_stop_name": name_map[s1],
                "to_stop_id": s2, "to_stop_name": name_map[s2],
                "effective_distance_m": round(eff_m, 1),
                "weekday_trips": int(r.weekday_trips),
                "routes": r.routes,
            })

    df_pairs = pd.DataFrame(rows).sort_values("effective_distance_m")
    os.makedirs("artifacts/data", exist_ok=True)
    out_path = "artifacts/data/downtown_corridor_thinning.csv"
    df_pairs.to_csv(out_path, index=False)
    print(f"✅ Analyzed {len(df_pairs)} weekday consecutive pairs. Saved to {out_path}")

if __name__ == "__main__":
    run_corridor_thinning()
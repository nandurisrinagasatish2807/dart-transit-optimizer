import os
from collections import Counter
import numpy as np
import pandas as pd
import osmnx as ox
import networkx as nx
import hdbscan
from sklearn.cluster import AgglomerativeClustering

# --- OSMnx 2.x settings ---
ox.settings.requests_timeout = 60
ox.settings.use_cache = True
ox.settings.log_console = False

# Edge types a pedestrian cannot or should not use
BAD_HIGHWAYS = {
    "motorway", "motorway_link", "cycleway", "construction",
    "proposed", "platform", "raceway", "abandoned", "bus_guideway"
}
BAD_SERVICE = {"drive-through", "parking_aisle", "driveway"}

# Ensure 'foot', 'service', and 'access' tags are preserved when reading XML
for tag in ("foot", "service", "access"):
    if tag not in ox.settings.useful_tags_way:
        ox.settings.useful_tags_way = list(ox.settings.useful_tags_way) + [tag]

OUTPUT_PATH = "artifacts/data/downtown_hdbscan_clusters.csv"

# Downtown Dallas core
NORTH, SOUTH, EAST, WEST = 32.785, 32.775, -96.790, -96.805

UNREACHABLE_M = 10_000.0   # distance assigned to stop pairs with no walking path
MAX_SEARCH_M = 3_000.0     # Dijkstra cutoff; anything farther counts as unreachable
MAX_CLUSTER_DIAMETER_M = 160.0  # Strict max walking distance between ANY two stops in a cluster


def _vals(x):
    if x is None:
        return set()
    return set(x) if isinstance(x, list) else {x}


def load_walk_graph():
    """Load the local OSM file and filter it down to a walkable network."""
    offline_file = "data/raw/downtown.osm"
    if not os.path.exists(offline_file):
        raise FileNotFoundError(
            f"Missing {offline_file}. Download it from the OSM API link and place it in data/raw/"
        )
    print(f"💾 Loading offline walk network from {offline_file}...")
    G = ox.graph_from_xml(offline_file, bidirectional=True, simplify=False)

    def drop_reason(d):
        hw = d.get("highway")
        if not hw:
            return "no_highway_tag"
        bad = _vals(hw) & BAD_HIGHWAYS
        if bad:
            return "bad_hw:" + sorted(bad)[0]
        if "no" in _vals(d.get("foot")):
            return "foot=no"
        if _vals(d.get("access")) & {"private", "no"}:
            return "access=private"
        svc = _vals(d.get("service"))
        if "private" in svc:
            return "service=private"
        if svc & BAD_SERVICE:
            return "service=" + sorted(svc & BAD_SERVICE)[0]
        return None

    drop, why = [], Counter()
    for u, v, k, d in G.edges(keys=True, data=True):
        r = drop_reason(d)
        if r:
            drop.append((u, v, k))
            why[r] += 1

    print(f"   removed {len(drop)} non-walkable edges: {dict(why)}")
    G.remove_edges_from(drop)
    G.remove_nodes_from(list(nx.isolates(G)))
    return ox.truncate.largest_component(G, strongly=False)


def attach_routes(downtown_stops):
    """Map GTFS route_ids to each stop in Downtown Dallas."""
    st_path, tr_path = "data/raw/stop_times.txt", "data/raw/trips.txt"
    if not (os.path.exists(st_path) and os.path.exists(tr_path)):
        downtown_stops["routes"] = [[] for _ in range(len(downtown_stops))]
        return downtown_stops

    stop_ids = set(downtown_stops["stop_id"].astype(str))
    st = pd.read_csv(st_path, usecols=["trip_id", "stop_id"], dtype=str)
    tr = pd.read_csv(tr_path, usecols=["trip_id", "route_id"], dtype=str)
    m = st[st["stop_id"].isin(stop_ids)].merge(tr, on="trip_id")
    route_map = m.groupby("stop_id")["route_id"].agg(lambda s: sorted(set(s))).to_dict()
    downtown_stops["routes"] = downtown_stops["stop_id"].astype(str).map(lambda x: route_map.get(x, []))
    return downtown_stops


def run_osmnx_hdbscan(stops_path):
    print("==================================================")
    print("🚶 DART Optimizer | Phase 6: OSMnx True-Walk Clustering")
    print("==================================================")

    # 1. Load stops and filter to Downtown Dallas
    stops = pd.read_csv(stops_path, dtype={"stop_id": str})
    mask = (
        (stops["stop_lat"] <= NORTH) & (stops["stop_lat"] >= SOUTH)
        & (stops["stop_lon"] <= EAST) & (stops["stop_lon"] >= WEST)
    )
    downtown_stops = stops[mask].copy().reset_index(drop=True)
    downtown_stops = attach_routes(downtown_stops)
    print(f"✅ Filtered to {len(downtown_stops)} stops in the Downtown Dallas bounding box.")

    # 2. Walking network
    G = load_walk_graph()
    print(f"✅ Walk network loaded: {len(G.nodes)} nodes and {len(G.edges)} edges.")

    # 3. Snap stops to nearest pedestrian nodes
    print("🔗 Snapping transit stops to pedestrian nodes...")
    downtown_stops["osm_node"] = ox.distance.nearest_nodes(
        G, X=downtown_stops["stop_lon"].values, Y=downtown_stops["stop_lat"].values
    )

    # 4. All-to-all street-network distance matrix
    print("📐 Calculating true walking distances...")
    n = len(downtown_stops)
    nodes = downtown_stops["osm_node"].tolist()
    dist_matrix = np.full((n, n), UNREACHABLE_M, dtype=np.float64)

    for i, src in enumerate(nodes):
        lengths = nx.single_source_dijkstra_path_length(
            G, src, cutoff=MAX_SEARCH_M, weight="length"
        )
        for j, dst in enumerate(nodes):
            if dst in lengths:
                dist_matrix[i, j] = lengths[dst]

    dist_matrix = np.minimum(dist_matrix, dist_matrix.T)
    np.fill_diagonal(dist_matrix, 0.0)

    # 5A. Reference HDBSCAN (leaf) for comparison
    hdb = hdbscan.HDBSCAN(
        metric="precomputed",
        min_cluster_size=3,
        min_samples=2,
        cluster_selection_method="leaf",
        cluster_selection_epsilon=100.0,
    )
    downtown_stops["hdbscan_raw_cluster"] = hdb.fit_predict(dist_matrix)

    # 5B. Complete-Linkage Clustering (Enforces strict max walking diameter, zero chaining)
    print(f"🧠 Running Complete-Linkage Walk Clustering (max diameter = {MAX_CLUSTER_DIAMETER_M:.0f}m)...")
    agg = AgglomerativeClustering(
        n_clusters=None,
        metric="precomputed",
        linkage="complete",
        distance_threshold=MAX_CLUSTER_DIAMETER_M,
    )
    raw_labels = agg.fit_predict(dist_matrix)
    counts = pd.Series(raw_labels).value_counts()

    # Re-index multi-stop clusters cleanly from 0 to K-1, singletons -> -1
    valid_old_ids = sorted([lbl for lbl, cnt in counts.items() if cnt >= 2])
    id_map = {old_id: new_id for new_id, old_id in enumerate(valid_old_ids)}
    downtown_stops["hdbscan_cluster"] = [id_map.get(lbl, -1) for lbl in raw_labels]

    # Compute cluster diameter and classify (Consolidation vs Transfer Hub)
    max_walks = np.zeros(n, dtype=np.float64)
    cluster_types = ["Standalone_Stop"] * n

    for cid, g in downtown_stops[downtown_stops["hdbscan_cluster"] >= 0].groupby("hdbscan_cluster"):
        idx = g.index.tolist()
        diam = float(dist_matrix[np.ix_(idx, idx)].max())
        route_sets = [set(r) for r in g["routes"]]
        has_duplicate_corridor = any(
            len(route_sets[a]) > 0 and route_sets[a] == route_sets[b]
            for a in range(len(route_sets)) for b in range(a + 1, len(route_sets))
        )
        ctype = "Consolidation_Candidate" if has_duplicate_corridor else "Transfer_Hub"
        for i in idx:
            max_walks[i] = round(diam, 1)
            cluster_types[i] = ctype

    downtown_stops["cluster_max_walk_m"] = max_walks
    downtown_stops["cluster_type"] = cluster_types
    downtown_stops["routes_str"] = downtown_stops["routes"].apply(lambda r: ", ".join(r))

    n_clusters = len(valid_old_ids)
    n_singleton = int((downtown_stops["hdbscan_cluster"] == -1).sum())
    type_counts = pd.Series(cluster_types).value_counts().to_dict()
    print(f"   ✅ Found {n_clusters} bounded walk clusters ({n_singleton} standalone stops).")
    print(f"   📊 Breakdown by stop role: {type_counts}")

    # 6. Save
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    downtown_stops.drop(columns=["routes"]).to_csv(OUTPUT_PATH, index=False)
    print(f"✅ SUCCESS: Saved true-walking clusters to {OUTPUT_PATH}")


if __name__ == "__main__":
    run_osmnx_hdbscan("data/raw/stops.txt")
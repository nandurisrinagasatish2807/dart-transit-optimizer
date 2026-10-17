import os
import time
from collections import Counter
import numpy as np
import pandas as pd
import osmnx as ox
import networkx as nx
import hdbscan

# --- OSMnx 2.x settings ---
ox.settings.requests_timeout = 60
ox.settings.use_cache = True
ox.settings.log_console = False

# Edge types a pedestrian cannot or should not use
BAD_HIGHWAYS = {"motorway", "motorway_link", "cycleway", "construction",
                "proposed", "platform", "raceway", "abandoned", "bus_guideway"}

# 'foot' isn't kept by default, so request it explicitly
ox.settings.useful_tags_way = ox.settings.useful_tags_way + ["foot"]

GRAPH_CACHE = "data/processed/downtown_walk.graphml"
OUTPUT_PATH = "artifacts/data/downtown_hdbscan_clusters.csv"

# Downtown Dallas core
NORTH, SOUTH, EAST, WEST = 32.785, 32.775, -96.790, -96.805

UNREACHABLE_M = 10_000.0   # distance assigned to stop pairs with no walking path
MAX_SEARCH_M = 3_000.0     # Dijkstra cutoff; anything farther counts as unreachable


def _vals(x):
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

    drop = []
    drop_reasons = Counter()
    for u, v, k, d in G.edges(keys=True, data=True):
        hw = d.get("highway")
        if not hw:
            drop.append((u, v, k))
            drop_reasons["no_highway_tag"] += 1
        elif _vals(hw) & BAD_HIGHWAYS:
            drop.append((u, v, k))
            for b in (_vals(hw) & BAD_HIGHWAYS):
                drop_reasons[f"bad_hw:{b}"] += 1
        elif "no" in _vals(d.get("foot")):
            drop.append((u, v, k))
            drop_reasons["foot=no"] += 1
        elif "private" in _vals(d.get("service")):
            drop.append((u, v, k))
            drop_reasons["service=private"] += 1

    G.remove_edges_from(drop)
    G.remove_nodes_from(list(nx.isolates(G)))
    G = ox.truncate.largest_component(G, strongly=False)
    print(f"   removed {len(drop)} non-walkable edges: {dict(drop_reasons)}")
    return G


def run_osmnx_hdbscan(stops_path):
    print("==================================================")
    print("🚶 DART Optimizer | Phase 6: OSMnx & HDBSCAN Walkability")
    print("==================================================")

    # 1. Load stops and filter to Downtown Dallas
    stops = pd.read_csv(stops_path)
    mask = (
        (stops["stop_lat"] <= NORTH) & (stops["stop_lat"] >= SOUTH)
        & (stops["stop_lon"] <= EAST) & (stops["stop_lon"] >= WEST)
    )
    downtown_stops = stops[mask].copy().reset_index(drop=True)
    print(f"✅ Filtered to {len(downtown_stops)} stops in the Downtown Dallas bounding box.")
    if len(downtown_stops) < 2:
        raise SystemExit("Need at least 2 stops to cluster. Check the bbox and stops.txt.")

    # 2. Walking network
    G = load_walk_graph()
    if len(G.nodes) == 0:
        raise SystemExit("Downloaded graph is empty. Check the bbox and file.")
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

    # Enforce symmetry and a zero diagonal
    dist_matrix = np.minimum(dist_matrix, dist_matrix.T)
    np.fill_diagonal(dist_matrix, 0.0)

    reachable = (dist_matrix < UNREACHABLE_M).sum() - n
    print(f"   {reachable // 2} of {n * (n - 1) // 2} stop pairs are walk-connected within {MAX_SEARCH_M:.0f} m")

    # 5. HDBSCAN on the precomputed street distances
    print("🧠 Running HDBSCAN variable-density clustering...")
    clusterer = hdbscan.HDBSCAN(
        metric="precomputed",
        min_cluster_size=3,
        min_samples=2,
        cluster_selection_method="leaf",
        cluster_selection_epsilon=100.0,
    )
    downtown_stops["hdbscan_cluster"] = clusterer.fit_predict(dist_matrix)

    n_clusters = downtown_stops["hdbscan_cluster"].max() + 1
    n_noise = int((downtown_stops["hdbscan_cluster"] == -1).sum())
    print(f"   Found {n_clusters} clusters; {n_noise} stops labeled noise (-1).")

    # --- diagnostics ---
    print("\n--- diagnostics ---")
    print("cluster sizes:", downtown_stops["hdbscan_cluster"].value_counts().sort_index().to_dict())

    _, snap_d = ox.distance.nearest_nodes(
        G, X=downtown_stops["stop_lon"].values, Y=downtown_stops["stop_lat"].values,
        return_dist=True,
    )
    print(f"snap distance m: median={np.median(snap_d):.0f}, max={np.max(snap_d):.0f}")

    lat = np.radians(downtown_stops["stop_lat"].values)
    lon = np.radians(downtown_stops["stop_lon"].values)
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat)[:, None] * np.cos(lat)[None, :] * np.sin(dlon / 2) ** 2
    straight = 2 * 6371000 * np.arcsin(np.sqrt(a))
    iu = np.triu_indices(n, k=1)
    keep = straight[iu] > 50
    ratio = dist_matrix[iu][keep] / straight[iu][keep]
    print(f"circuity: median={np.median(ratio):.2f}, p5={np.percentile(ratio, 5):.2f}, p95={np.percentile(ratio, 95):.2f}")

    for method in ("eom", "leaf"):
        for mcs in (2, 3):
            for eps in (0, 80, 120, 150):
                lab = hdbscan.HDBSCAN(
                    metric="precomputed",
                    min_cluster_size=mcs,
                    min_samples=2,
                    cluster_selection_method=method,
                    cluster_selection_epsilon=float(eps),
                ).fit_predict(dist_matrix)
                sizes = sorted(np.bincount(lab[lab >= 0]).tolist(), reverse=True)[:8]
                print(f"method={method:<4} | mcs={mcs} | eps={eps:>3}m -> clusters={lab.max() + 1:>2}, noise={(lab == -1).sum():>2}, top sizes={sizes}")

    # 6. Save
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    downtown_stops.to_csv(OUTPUT_PATH, index=False)
    print(f"\n✅ SUCCESS: Saved true-walking clusters to {OUTPUT_PATH}")


if __name__ == "__main__":
    run_osmnx_hdbscan("data/raw/stops.txt")
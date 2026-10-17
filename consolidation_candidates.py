"""Rule-based stop-consolidation REVIEW list (not a recommendation).

A pair is flagged only if both stops are
  - on the same street (first part of the stop name),
  - going the same direction (N/S/E/W parsed from the name),
  - served by exactly the same set of route_ids, and
  - within THRESHOLD_M of each other by walking distance on the OSM graph.

Run from the dart_data folder:  python consolidation_candidates.py
Needs: artifacts/data/downtown_hdbscan_clusters.csv (has osm_node),
       data/raw/stop_times.txt, data/raw/trips.txt, optional data/raw/routes.txt
"""
import re
import numpy as np
import pandas as pd
import networkx as nx
from src.dart_optimizer.optimizer.walk_cluster import load_walk_graph

THRESHOLD_M = 160.0
CLUSTERS = "artifacts/data/downtown_hdbscan_clusters.csv"

df = pd.read_csv(CLUSTERS, dtype={"stop_id": str})
st = pd.read_csv("data/raw/stop_times.txt", usecols=["trip_id", "stop_id"], dtype=str)
tr = pd.read_csv("data/raw/trips.txt", usecols=["trip_id", "route_id"], dtype=str)
m = st[st["stop_id"].isin(df["stop_id"])].merge(tr, on="trip_id")
df["routes"] = df["stop_id"].map(m.groupby("stop_id")["route_id"].agg(frozenset))

try:  # optional: readable route names
    rt = pd.read_csv("data/raw/routes.txt", dtype=str)
    names = dict(zip(rt["route_id"], rt["route_short_name"]))
except Exception:
    names = {}

# Parse "STREET @ CROSS - DIR - POS" (suffix spacing in the feed is inconsistent)
pat = re.compile(
    r"^(?P<street>.+?)\s*@\s*(?P<cross>.+?)\s*-\s*(?P<dir>[NSEW])\s*-\s*(?P<pos>NS|FS|MB)\s*$"
)
parsed = df["stop_name"].str.strip().str.extract(pat)
df = pd.concat([df, parsed], axis=1)
print(f"Parsed street/direction for {parsed['dir'].notna().sum()} of {len(df)} stops "
      f"(unparsed ones, e.g. stations and transfer centers, are skipped)")

# Walking distances (only need pairs within the threshold)
G = load_walk_graph()
nodes = df["osm_node"].tolist()
reach = [
    nx.single_source_dijkstra_path_length(G, s, cutoff=THRESHOLD_M, weight="length")
    for s in nodes
]


def walk(i, j):
    return min(reach[i].get(nodes[j], np.inf), reach[j].get(nodes[i], np.inf))


def route_label(rs):
    labels = sorted(names.get(r, r) for r in rs)
    s = ",".join(labels)
    return s if len(s) <= 40 else f"{len(labels)} routes"


rows = []
sub = df.dropna(subset=["dir"])
for (street, d, rs), g in sub.groupby(["street", "dir", "routes"]):
    if len(g) < 2:
        continue
    idx = g.index.tolist()
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            w = walk(idx[a], idx[b])
            if w <= THRESHOLD_M:
                ra, rb = df.loc[idx[a]], df.loc[idx[b]]
                rows.append((w, street, d, ra["stop_name"], rb["stop_name"], route_label(rs)))

rows.sort()
print(f"\n{len(rows)} candidate pairs within {THRESHOLD_M:.0f} m "
      f"(same street, same direction, identical routes)\n")
for w, street, d, a, b, rl in rows:
    print(f"{w:5.0f} m | {street} {d}B | {a}  <->  {b} | {rl}")
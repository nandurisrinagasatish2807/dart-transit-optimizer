"""Corridor thinning REVIEW list for Downtown Dallas (one weekday of service).

Why this exists: flagging every close pair on its own doesn't work, because
removing one stop lengthens its neighbours' gaps. This walks each route
pattern's actual in-box stop sequence and decides which stops could go so that
the remaining neighbours are at least MIN_SPACING apart, without creating a
gap larger than MAX_GAP.

Rules
  - A stop is flagged only if it can go on EVERY route pattern that serves it.
  - First and last stop of every in-box run are kept (what lies beyond the box
    is unknown). Stations/transfer centers (names without "- DIR - POS") are
    never flagged.
  - Accessibility: a stop with wheelchair_boarding = 1 is flagged only if the
    stop it merges into is also 1. (0 / blank means "no information" in GTFS,
    not "inaccessible".)

Outputs
  - artifacts/data/downtown_thinning_review.csv       flagged stops + the stop each merges into
  - artifacts/data/downtown_thinning_blocked_pairs.csv close pairs NOT flagged, with the reason

This is a review list, not a recommendation: GTFS has no boardings or curb
data. Distance between consecutive stops = max(walk between snapped OSM nodes,
straight line). Distance along a run = sum of those gaps (a walking proxy for
the bus path). Which stop of a close pair gets flagged is mechanical (the
downstream one); treat it as "one of these two".

Run from the dart_data folder:
  $env:PYTHONPATH="src"; python -m dart_optimizer.optimizer.corridor_thinning
"""
import os
import re
from collections import defaultdict

import numpy as np
import pandas as pd
import networkx as nx
import osmnx as ox

try:
    from dart_optimizer.optimizer.walk_cluster import load_walk_graph, NORTH, SOUTH, EAST, WEST
except ImportError:
    from src.dart_optimizer.optimizer.walk_cluster import load_walk_graph, NORTH, SOUTH, EAST, WEST

SERVICE_DATE = "20260722"          # a Wednesday inside calendar.txt's range
MIN_SPACINGS_M = (100.0, 130.0, 160.0)
MAX_GAP_M = float(os.environ.get("MAX_GAP_M", "300.0"))                  # placeholder: replace with an agency standard
UNREACHABLE_M = 10_000.0
OUT_PATH = "artifacts/data/downtown_thinning_review.csv"
BLOCKED_PATH = "artifacts/data/downtown_thinning_blocked_pairs.csv"
DIR_POS = re.compile(r"-\s*[NSEW]\s*-\s*(NS|FS|MB)\s*$")

WHY_TEXT = {
    "end": "run end (next stop is outside the box)",
    "protected": "station / transfer center",
    "far_enough": "already >= min spacing from the previous kept stop",
    "gap_cap": "merging would exceed MAX_GAP_M",
    "accessibility": "accessible stop would merge into a stop not marked accessible",
    "dropped": "dropped",
}


def why_text(code):
    prefix = "needed_on_other_pattern"
    if code.startswith(prefix):
        return "kept for another route pattern " + code[len(prefix):]
    return WHY_TEXT.get(code, code)


def wc_label(v):
    return {"1": "accessible", "2": "not accessible"}.get(str(v), "no info")


def haversine_m(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(np.radians, (lat1, lon1, lat2, lon2))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return float(2 * 6371000 * np.arcsin(np.sqrt(h)))


def active_trip_ids(trips):
    """Trips running on SERVICE_DATE (calendar.txt, plus calendar_dates.txt if present)."""
    services = set()
    if os.path.exists("data/raw/calendar.txt"):
        day = pd.Timestamp(SERVICE_DATE).day_name().lower()
        cal = pd.read_csv("data/raw/calendar.txt", dtype=str)
        on = cal[(cal[day] == "1")
                 & (cal["start_date"] <= SERVICE_DATE)
                 & (cal["end_date"] >= SERVICE_DATE)]
        services |= set(on["service_id"])
    if os.path.exists("data/raw/calendar_dates.txt"):
        cd = pd.read_csv("data/raw/calendar_dates.txt", dtype=str)
        cd = cd[cd["date"] == SERVICE_DATE]
        services |= set(cd[cd["exception_type"] == "1"]["service_id"])
        services -= set(cd[cd["exception_type"] == "2"]["service_id"])
    return set(trips[trips["service_id"].isin(services)]["trip_id"])


def thin(seq, gaps, min_spacing, max_gap, forced, wc):
    """Thin one ordered run.

    Returns (keep, anchor, why), one entry per stop:
      keep[i]  False if the stop is dropped
      anchor[i] the last kept stop it merges into (None if kept)
      why[i]    reason code ('dropped' or why it was kept)
    forced maps stop_id -> reason label for stops that must be kept.
    """
    n = len(seq)
    keep = [True] * n
    anchor = [None] * n
    why = [""] * n
    why[0] = why[-1] = "end"
    last = 0
    for i in range(1, n - 1):
        s = seq[i]
        if s in forced:
            why[i] = forced[s]
            last = i
            continue
        d_to_i = sum(gaps[last:i])         # last kept -> this stop
        d_to_next = sum(gaps[last:i + 1])   # last kept -> the stop after this one
        if d_to_i >= min_spacing:
            why[i] = "far_enough"
            last = i
        elif d_to_next > max_gap:
            why[i] = "gap_cap"
            last = i
        elif wc.get(s) == "1" and wc.get(seq[last]) != "1":
            why[i] = "accessibility"
            last = i
        else:
            keep[i] = False
            anchor[i] = seq[last]
            why[i] = "dropped"
    return keep, anchor, why


def solve(patterns, gap_of, min_spacing, protected, wc):
    """Stops removable on every pattern that serves them (iterates to resolve conflicts).

    Returns (removable, anchors, forced): anchors[stop] = set of stops it merges into.
    """
    forced = {s: "protected" for s in protected}
    while True:
        dropped, appears = defaultdict(int), defaultdict(int)
        anchors, seen = defaultdict(set), defaultdict(set)
        for seq in patterns:
            gaps = [gap_of[(a, b)] for a, b in zip(seq[:-1], seq[1:])]
            keep, anchor, why = thin(seq, gaps, min_spacing, MAX_GAP_M, forced, wc)
            for s, k, a, w in zip(seq, keep, anchor, why):
                appears[s] += 1
                seen[s].add(w)
                if not k:
                    dropped[s] += 1
                    anchors[s].add(a)
        conflict = {s for s in dropped if dropped[s] < appears[s]} - set(forced)
        if not conflict:
            removable = {s for s in dropped if dropped[s] == appears[s]}
            return removable, anchors, forced
        for s in conflict:
            blockers = sorted(seen[s] - {"dropped"})
            forced[s] = "needed_on_other_pattern(" + ",".join(blockers) + ")"


def pair_reasons(patterns, pair, gap_of, min_spacing, forced, wc):
    """Why each stop of a close pair was kept, on the patterns where the pair occurs."""
    ra, rb = set(), set()
    for seq in patterns:
        for i in range(len(seq) - 1):
            if (seq[i], seq[i + 1]) == pair:
                gaps = [gap_of[(x, y)] for x, y in zip(seq[:-1], seq[1:])]
                _, _, why = thin(seq, gaps, min_spacing, MAX_GAP_M, forced, wc)
                ra.add(why[i])
                rb.add(why[i + 1])
    return ra, rb


def main():
    print("==================================================")
    print("???  DART Optimizer | Corridor Thinning Review List")
    print("==================================================")

    stops = pd.read_csv("data/raw/stops.txt", dtype=str)
    stops["stop_lat"] = stops["stop_lat"].astype(float)
    stops["stop_lon"] = stops["stop_lon"].astype(float)
    dt = stops[(stops["stop_lat"] <= NORTH) & (stops["stop_lat"] >= SOUTH)
               & (stops["stop_lon"] <= EAST) & (stops["stop_lon"] >= WEST)].copy().reset_index(drop=True)
    dt_ids = set(dt["stop_id"])
    name = dict(zip(dt["stop_id"], dt["stop_name"]))
    lat = dict(zip(dt["stop_id"], dt["stop_lat"]))
    lon = dict(zip(dt["stop_id"], dt["stop_lon"]))
    wc = (dict(zip(dt["stop_id"], dt["wheelchair_boarding"]))
          if "wheelchair_boarding" in dt.columns else {})
    if not wc:
        print("note: stops.txt has no wheelchair_boarding column; accessibility rule is inactive")
    protected = {sid for sid, nm in name.items() if not DIR_POS.search(nm.strip())}

    G = load_walk_graph()
    dt["osm_node"] = ox.distance.nearest_nodes(G, X=dt["stop_lon"].values, Y=dt["stop_lat"].values)
    node = dict(zip(dt["stop_id"], dt["osm_node"]))

    trips = pd.read_csv("data/raw/trips.txt", dtype=str)
    rt = pd.read_csv("data/raw/routes.txt", usecols=["route_id", "route_short_name"], dtype=str)
    trips = trips.merge(rt, on="route_id", how="left")
    day_trips = active_trip_ids(trips)
    print(f"Service date {SERVICE_DATE}: {len(day_trips)} active trips")

    st = pd.read_csv("data/raw/stop_times.txt",
                     usecols=["trip_id", "stop_id", "stop_sequence"],
                     dtype={"trip_id": str, "stop_id": str, "stop_sequence": int})
    st = st[st["trip_id"].isin(day_trips)].sort_values(["trip_id", "stop_sequence"])
    st["in_box"] = st["stop_id"].isin(dt_ids)
    # A new "run" starts each time a trip re-enters the box
    st["run"] = (~st["in_box"]).astype(int).groupby(st["trip_id"]).cumsum()
    box = st[st["in_box"]]

    runs = box.groupby(["trip_id", "run"])["stop_id"].agg(tuple)
    patterns = {seq for seq in runs if len(seq) >= 2}
    pair_trips = defaultdict(int)
    for seq in runs:
        for a, b in zip(seq[:-1], seq[1:]):
            pair_trips[(a, b)] += 1
    print(f"{box['stop_id'].nunique()} in-box stops with service; {len(patterns)} distinct in-box stop sequences")

    gap_of = {}
    for a, b in pair_trips:
        straight = haversine_m(lat[a], lon[a], lat[b], lon[b])
        try:
            walk = float(nx.shortest_path_length(G, node[a], node[b], weight="length"))
        except nx.NetworkXNoPath:
            walk = UNREACHABLE_M
        gap_of[(a, b)] = max(walk, straight)

    routes_at = (box.merge(trips[["trip_id", "route_short_name"]], on="trip_id")
                 .groupby("stop_id")["route_short_name"]
                 .agg(lambda s: sorted(set(s.dropna()))))
    trips_at = box.groupby("stop_id")["trip_id"].nunique()

    rows, blocked_rows = [], []
    for ms in MIN_SPACINGS_M:
        removable, anchors, forced = solve(patterns, gap_of, ms, protected, wc)
        print(f"\n=== min spacing {ms:.0f} m, max merged gap {MAX_GAP_M:.0f} m: "
              f"{len(removable)} stops flagged for review ===")
        for sid in sorted(removable, key=lambda s: name[s]):
            rts = routes_at.get(sid, [])
            trips_n = int(trips_at.get(sid, 0))
            anc = sorted(anchors[sid], key=lambda s: name[s])
            anc_txt = " | ".join(f"{name[a]} ({wc_label(wc.get(a))})" for a in anc)
            print(f"  {name[sid]:<34} trips {trips_n:>4} | {len(rts):>2} routes: {','.join(rts)[:40]}")
            print(f"      {wc_label(wc.get(sid))}; merges into: {anc_txt}")
            rows.append({
                "min_spacing_m": ms, "stop_id": sid, "stop_name": name[sid],
                "weekday_trips_at_stop": trips_n, "route_count": len(rts),
                "routes": ", ".join(rts),
                "wheelchair": wc_label(wc.get(sid)),
                "merges_into": " | ".join(name[a] for a in anc),
                "merges_into_wheelchair": " | ".join(wc_label(wc.get(a)) for a in anc),
            })

        close = sorted((g, p) for p, g in gap_of.items() if g < ms)
        unresolved = [(g, p) for g, p in close if p[0] not in removable and p[1] not in removable]
        print(f"\n  Close pairs (< {ms:.0f} m) NOT flagged, and why: {len(unresolved)} of {len(close)}")
        for g, (a, b) in unresolved:
            ra, rb = pair_reasons(patterns, (a, b), gap_of, ms, forced, wc)
            ta = "; ".join(sorted(why_text(x) for x in ra))
            tb = "; ".join(sorted(why_text(x) for x in rb))
            print(f"    {g:4.0f} m | {pair_trips[(a, b)]:>4} trips | {name[a]}  ->  {name[b]}")
            print(f"           first: {ta}")
            print(f"           second: {tb}")
            blocked_rows.append({
                "min_spacing_m": ms, "from_stop_id": a, "from_stop_name": name[a],
                "to_stop_id": b, "to_stop_name": name[b], "gap_m": round(g, 1),
                "weekday_trips": pair_trips[(a, b)],
                "from_reasons": ta, "to_reasons": tb,
            })

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT_PATH, index=False)
    pd.DataFrame(blocked_rows).to_csv(BLOCKED_PATH, index=False)
    print(f"\n? Saved {OUT_PATH}")
    print(f"? Saved {BLOCKED_PATH}")


if __name__ == "__main__":
    main()

import os

import numpy as np
import pandas as pd

from dart_optimizer.transfers.metrics import (
    TransferMetricsConfig,
    assign_severity,
    calculate_wait_fraction,
)


def time_to_seconds(time_str):
    """Converts GTFS HH:MM:SS to total seconds, handling >24h times."""
    if pd.isna(time_str):
        return np.nan
    try:
        h, m, s = map(int, str(time_str).strip().split(':'))
        return h * 3600 + m * 60 + s
    except Exception:
        return np.nan

def generate_transfer_events():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 1: Event-Level Schema (Route-Direction Safe)")
    print(f"{'='*50}")
    
    raw_dir = "data/raw"
    if not os.path.exists(f"{raw_dir}/stop_times.txt"):
        print(f"❌ Error: Raw GTFS data not found in {raw_dir}.")
        return

    # Load base tables
    trips = pd.read_csv(f"{raw_dir}/trips.txt")
    stop_times = pd.read_csv(f"{raw_dir}/stop_times.txt")
    routes = pd.read_csv(f"{raw_dir}/routes.txt")

    # Merge route names and info
    trips_routes = trips.merge(routes, on='route_id', how='left')
    
    # Process stop times and convert arrival/departure times
    stop_times['arrival_sec'] = stop_times['arrival_time'].apply(time_to_seconds)
    stop_times['departure_sec'] = stop_times['departure_time'].apply(time_to_seconds)

    # Combine with trip details
    full_events = stop_times.merge(trips_routes, on='trip_id', how='inner')

    # Separate arrivals and departures
    arrivals = full_events[['trip_id', 'route_id', 'route_short_name', 'direction_id', 'stop_id', 'service_id', 'arrival_sec']].copy()
    arrivals.rename(columns={
        'trip_id': 'arrival_trip_id',
        'route_id': 'route_arr_id',
        'route_short_name': 'route_arr_name',
        'direction_id': 'dir_arr',
        'arrival_sec': 'scheduled_arrival_sec'
    }, inplace=True)

    departures = full_events[['trip_id', 'route_id', 'route_short_name', 'direction_id', 'stop_id', 'service_id', 'departure_sec']].copy()
    departures.rename(columns={
        'trip_id': 'departure_trip_id',
        'route_id': 'route_dep_id',
        'route_short_name': 'route_dep_name',
        'direction_id': 'dir_dep',
        'departure_sec': 'departure_sec'
    }, inplace=True)

    # Apply standard 120s walking buffer
    arrivals['walking_time_sec'] = 120
    arrivals['passenger_ready_sec'] = arrivals['scheduled_arrival_sec'] + arrivals['walking_time_sec']

    print("Expanding arrivals against valid outbound route-direction pairs...")
    
    # 1. Create a distinct menu of all valid outbound routes from each stop + service combination
    outbound_menu = departures[['stop_id', 'service_id', 'route_dep_id', 'route_dep_name', 'dir_dep']].drop_duplicates()
    
    # 2. Expand arrivals against this menu
    arrivals_expanded = arrivals.merge(outbound_menu, on=['stop_id', 'service_id'], how='inner')
    
    # 3. Filter out same route/direction loops BEFORE the heavy merge
    arrivals_expanded = arrivals_expanded[
        (arrivals_expanded['route_arr_id'] != arrivals_expanded['route_dep_id']) | 
        (arrivals_expanded['dir_arr'] != arrivals_expanded['dir_dep'])
    ].copy()

    print("Computing rolling nearest-match strictly grouped by Route and Direction...")
    
    # Sort for merge_asof requirements
    arrivals_expanded = arrivals_expanded.sort_values('passenger_ready_sec')
    departures = departures.sort_values('departure_sec')

    match_keys = ['stop_id', 'service_id', 'route_dep_id', 'dir_dep']

    next_deps = pd.merge_asof(
        arrivals_expanded, departures, 
        left_on='passenger_ready_sec', right_on='departure_sec', 
        by=match_keys, direction='forward', suffixes=('', '_drop')
    )
    
    prev_deps = pd.merge_asof(
        arrivals_expanded, departures, 
        left_on='passenger_ready_sec', right_on='departure_sec', 
        by=match_keys, direction='backward', suffixes=('', '_prev')
    )
    
    events = next_deps.copy()
    events['next_departure_sec'] = events['departure_sec']
    events['next_departure_trip_id'] = events['departure_trip_id']
    events['previous_departure_sec'] = prev_deps['departure_sec']
    events['previous_departure_trip_id'] = prev_deps['departure_trip_id']
    
    print("Applying Phase 2 Metrics Formulas...")
    events['miss_margin_sec'] = events['passenger_ready_sec'] - events['previous_departure_sec']
    events['next_wait_sec'] = events['next_departure_sec'] - events['passenger_ready_sec']
    events['scheduled_headway_sec'] = events['next_departure_sec'] - events['previous_departure_sec']
    
    # Wait Fraction & Near-Miss Flag
    events['wait_fraction_of_headway'] = calculate_wait_fraction(events['next_wait_sec'], events['scheduled_headway_sec'])
    events['is_near_miss'] = (
        (events['miss_margin_sec'] > 0) & 
        (events['miss_margin_sec'] <= TransferMetricsConfig.NEAR_MISS_MAX_MARGIN_SEC) & 
        (events['next_wait_sec'] >= TransferMetricsConfig.NEAR_MISS_MIN_WAIT_SEC)
    )
    
    # Categorical Severity Levels
    events['severity'] = assign_severity(events['next_wait_sec'])
    
    final_cols = [
        'stop_id', 'service_id', 'arrival_trip_id', 'route_arr_id', 'route_arr_name', 'dir_arr',
        'scheduled_arrival_sec', 'passenger_ready_sec', 'walking_time_sec',
        'route_dep_id', 'route_dep_name', 'dir_dep',
        'previous_departure_trip_id', 'previous_departure_sec',
        'next_departure_trip_id', 'next_departure_sec',
        'miss_margin_sec', 'next_wait_sec', 'scheduled_headway_sec', 
        'wait_fraction_of_headway', 'severity', 'is_near_miss'
    ]
    
    events = events[final_cols].dropna(subset=['previous_departure_sec', 'next_departure_sec'])
    os.makedirs("artifacts/data", exist_ok=True)
    out_file = "artifacts/data/transfer_events.csv"
    events.to_csv(out_file, index=False)
    
    print(f"\n✅ SUCCESS: Route-Direction Safe Transfer Events Generated: {len(events):,}")
    print(f"   Saved validated schema to: {out_file}")

if __name__ == "__main__":
    generate_transfer_events()
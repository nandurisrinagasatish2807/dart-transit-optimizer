import os
import numpy as np
import pandas as pd

from dart_optimizer.gtfs.calendar import get_active_services
from dart_optimizer.transfers.metrics import (
    TransferMetricsConfig,
    assign_severity,
    calculate_wait_fraction,
)

def time_to_seconds(time_str):
    if pd.isna(time_str):
        return np.nan
    try:
        h, m, s = map(int, str(time_str).strip().split(':'))
        return h * 3600 + m * 60 + s
    except ValueError:
        return np.nan

def match_transfers(stop_times, trips_routes, hubs=None):
    """
    Unified transfer matching logic shared by both the baseline audit and the simulator.
    Enforces boarding eligibility (pickup/drop_off types) and precise route/direction grouping.
    """
    # 1. Group by hub_id if hubs are provided, otherwise default to stop_id
    if hubs is not None:
        full_events = stop_times.merge(hubs[['stop_id', 'hub_id']], on='stop_id', how='inner')
        loc_key = 'hub_id'
    else:
        full_events = stop_times.copy()
        loc_key = 'stop_id'
        
    full_events = full_events.merge(trips_routes, on='trip_id', how='inner')

    # 2. Apply GTFS Boarding Rules (The logic previously missing from the simulator)
    valid_arrivals = full_events[full_events['drop_off_type'].fillna(0) != 1].copy()
    valid_departures = full_events[full_events['pickup_type'].fillna(0) != 1].copy()

    # 3. Rename columns for Arrivals
    arr_cols = ['trip_id', 'route_id', 'route_short_name', 'direction_id', 'stop_id', 'service_id', 'block_id', 'stop_sequence', 'arrival_sec'] + ([loc_key] if loc_key == 'hub_id' else [])
    arrivals = valid_arrivals[arr_cols].copy()
    arrivals.rename(columns={
        'trip_id': 'arrival_trip_id', 'route_id': 'route_arr_id',
        'route_short_name': 'route_arr_name', 'direction_id': 'dir_arr',
        'service_id': 'arrival_service_id', 'block_id': 'arrival_block_id',
        'stop_sequence': 'arrival_stop_sequence', 'arrival_sec': 'scheduled_arrival_sec'
    }, inplace=True)

    # 4. Rename columns for Departures
    dep_cols = ['trip_id', 'route_id', 'route_short_name', 'direction_id', 'stop_id', 'service_id', 'block_id', 'stop_sequence', 'departure_sec'] + ([loc_key] if loc_key == 'hub_id' else [])
    departures = valid_departures[dep_cols].copy()
    departures.rename(columns={
        'trip_id': 'departure_trip_id', 'route_id': 'route_dep_id',
        'route_short_name': 'route_dep_name', 'direction_id': 'dir_dep',
        'service_id': 'departure_service_id', 'block_id': 'departure_block_id',
        'stop_sequence': 'departure_stop_sequence', 'departure_sec': 'departure_sec'
    }, inplace=True)

    arrivals['walking_time_sec'] = 120
    arrivals['passenger_ready_sec'] = arrivals['scheduled_arrival_sec'] + arrivals['walking_time_sec']

    # 5. Expand and Match
    outbound_menu = departures[[loc_key, 'route_dep_id', 'route_dep_name', 'dir_dep']].drop_duplicates()
    arrivals_expanded = arrivals.merge(outbound_menu, on=[loc_key], how='inner')
    
    arrivals_expanded = arrivals_expanded[
        (arrivals_expanded['route_arr_id'] != arrivals_expanded['route_dep_id']) | 
        (arrivals_expanded['dir_arr'] != arrivals_expanded['dir_dep'])
    ].copy()

    arrivals_expanded = arrivals_expanded.sort_values('passenger_ready_sec').reset_index(drop=True)
    departures = departures.sort_values('departure_sec').reset_index(drop=True)
    match_keys = [loc_key, 'route_dep_id', 'dir_dep']

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
    events['previous_departure_service_id'] = prev_deps['departure_service_id']
    events['previous_departure_block_id'] = prev_deps['departure_block_id']
    
    events = events.dropna(subset=['previous_departure_sec', 'next_departure_sec']).copy()
    events['miss_margin_sec'] = events['passenger_ready_sec'] - events['previous_departure_sec']
    events['next_wait_sec'] = events['next_departure_sec'] - events['passenger_ready_sec']
    events['scheduled_headway_sec'] = events['next_departure_sec'] - events['previous_departure_sec']
    
    events['wait_fraction_of_headway'] = calculate_wait_fraction(events['next_wait_sec'], events['scheduled_headway_sec'])
    events['is_near_miss'] = (
        (events['miss_margin_sec'] > 0) & 
        (events['miss_margin_sec'] <= TransferMetricsConfig.NEAR_MISS_MAX_MARGIN_SEC) & 
        (events['next_wait_sec'] >= TransferMetricsConfig.NEAR_MISS_MIN_WAIT_SEC)
    )
    events['severity'] = assign_severity(events['next_wait_sec'])
    
    return events


def generate_transfer_events(target_date_str="20260722"):
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 1: Event-Level Schema (Unified Matcher)")
    print(f"{'='*50}")
    
    raw_dir = "data/raw"
    if not os.path.exists(f"{raw_dir}/stop_times.txt"):
        raw_dir = "."

    active_services = get_active_services(target_date_str, gtfs_dir=raw_dir)

    trips_cols = pd.read_csv(f"{raw_dir}/trips.txt", nrows=0).columns
    use_trips = ['trip_id', 'route_id', 'service_id']
    if 'direction_id' in trips_cols: use_trips.append('direction_id')
    if 'block_id' in trips_cols: use_trips.append('block_id')
        
    trips = pd.read_csv(f"{raw_dir}/trips.txt", usecols=use_trips, dtype={'service_id': str, 'block_id': str, 'trip_id': str, 'route_id': str})
    if 'direction_id' not in trips.columns: trips['direction_id'] = 0
    if 'block_id' not in trips.columns: trips['block_id'] = 'UNKNOWN'
        
    trips = trips[trips['service_id'].isin(active_services)].copy()

    stop_times = pd.read_csv(f"{raw_dir}/stop_times.txt", dtype={'trip_id': str, 'stop_id': str})
    for col in ['pickup_type', 'drop_off_type']:
        if col not in stop_times.columns: stop_times[col] = 0
    if 'stop_sequence' not in stop_times.columns: stop_times['stop_sequence'] = 0

    routes = pd.read_csv(f"{raw_dir}/routes.txt", dtype={'route_id': str})
    trips_routes = trips.merge(routes, on='route_id', how='left')
    
    stop_times['arrival_sec'] = stop_times['arrival_time'].apply(time_to_seconds)
    stop_times['departure_sec'] = stop_times['departure_time'].apply(time_to_seconds)

    print("Executing shared match_transfers function...")
    events = match_transfers(stop_times, trips_routes, hubs=None)
    
    events['analysis_date'] = target_date_str
    
    final_cols = [
        'analysis_date', 'stop_id', 
        'arrival_service_id', 'arrival_block_id', 'arrival_trip_id', 'route_arr_id', 'route_arr_name', 'dir_arr', 'arrival_stop_sequence',
        'scheduled_arrival_sec', 'passenger_ready_sec', 'walking_time_sec',
        'departure_service_id', 'departure_block_id', 'route_dep_id', 'route_dep_name', 'dir_dep', 'departure_stop_sequence',
        'previous_departure_trip_id', 'previous_departure_sec', 'previous_departure_block_id',
        'next_departure_trip_id', 'next_departure_sec',
        'miss_margin_sec', 'next_wait_sec', 'scheduled_headway_sec', 
        'wait_fraction_of_headway', 'severity', 'is_near_miss'
    ]
    
    events = events[final_cols]
    os.makedirs("artifacts/data", exist_ok=True)
    out_file = "artifacts/data/transfer_events.csv"
    events.to_csv(out_file, index=False)
    
    print(f"\n✅ SUCCESS: Boarding-Eligible Transfer Events Generated: {len(events):,}")
    print(f"   Saved validated schema to: {out_file}")

if __name__ == "__main__":
    generate_transfer_events()
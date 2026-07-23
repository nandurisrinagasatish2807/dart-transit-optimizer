import pandas as pd
import numpy as np
import os
from dart_optimizer.transfers.metrics import TransferMetricsConfig, assign_severity, calculate_wait_fraction

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
    print("🚇 DART Optimizer | Phase 1: Event-Level Schema")
    print(f"{'='*50}")
    
    raw_dir = "data/raw"
    if not os.path.exists(f"{raw_dir}/stop_times.txt"):
        print(f"❌ Error: GTFS files not found in '{raw_dir}/'.")
        return

    print("Loading GTFS datasets...")
    stop_times = pd.read_csv(f"{raw_dir}/stop_times.txt", dtype=str)
    trips = pd.read_csv(f"{raw_dir}/trips.txt", dtype=str)
    routes = pd.read_csv(f"{raw_dir}/routes.txt", dtype=str)
    
    print("Joining trips and routes to stop events...")
    events = stop_times.merge(trips[['trip_id', 'route_id', 'direction_id', 'service_id']], on='trip_id', how='inner')
    events = events.merge(routes[['route_id', 'route_short_name']], on='route_id', how='left')
    
    print("Converting GTFS times to absolute seconds...")
    events['arrival_sec'] = events['arrival_time'].apply(time_to_seconds)
    events['departure_sec'] = events['departure_time'].apply(time_to_seconds)
    events = events.dropna(subset=['arrival_sec', 'departure_sec'])
    
    events = events.sort_values(by=['stop_id', 'service_id', 'departure_sec'])
    
    os.makedirs("artifacts/data", exist_ok=True)
    out_file = "artifacts/data/staged_events.csv"
    events.to_csv(out_file, index=False)
    print(f"✅ Formatted {len(events):,} stop events to {out_file}")

def build_transfer_events():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 2: Corrected Metrics & Severity")
    print(f"{'='*50}")
    
    staged_file = "artifacts/data/staged_events.csv"
    if not os.path.exists(staged_file):
        print(f"❌ Error: {staged_file} not found.")
        return

    df = pd.read_csv(staged_file, low_memory=False)
    df['arrival_sec'] = pd.to_numeric(df['arrival_sec'], errors='coerce')
    df['departure_sec'] = pd.to_numeric(df['departure_sec'], errors='coerce')
    df = df.dropna(subset=['arrival_sec', 'departure_sec']).sort_values('departure_sec')
    
    walking_time_sec = 120
    
    for col in ['direction_id', 'route_short_name']:
        if col not in df.columns:
            df[col] = "UNKNOWN"
            
    arrivals = df.rename(columns={
        'trip_id': 'arrival_trip_id',
        'route_id': 'route_arr_id',
        'route_short_name': 'route_arr_name',
        'direction_id': 'dir_arr',
        'arrival_sec': 'scheduled_arrival_sec'
    }).drop(columns=['departure_sec'])
    
    arrivals['passenger_ready_sec'] = arrivals['scheduled_arrival_sec'] + walking_time_sec
    arrivals['walking_time_sec'] = walking_time_sec
    arrivals = arrivals.sort_values('passenger_ready_sec')

    departures = df.rename(columns={
        'trip_id': 'departure_trip_id',
        'route_id': 'route_dep_id',
        'route_short_name': 'route_dep_name',
        'direction_id': 'dir_dep'
    }).drop(columns=['arrival_sec'])

    print("Computing rolling nearest-match (Next & Previous Departures)...")
    next_deps = pd.merge_asof(arrivals, departures, left_on='passenger_ready_sec', right_on='departure_sec', by=['stop_id', 'service_id'], direction='forward', suffixes=('', '_drop'))
    prev_deps = pd.merge_asof(arrivals, departures, left_on='passenger_ready_sec', right_on='departure_sec', by=['stop_id', 'service_id'], direction='backward', suffixes=('', '_prev'))
    
    events = next_deps.copy()
    events['next_departure_sec'] = events['departure_sec']
    events['next_departure_trip_id'] = events['departure_trip_id']
    events['previous_departure_sec'] = prev_deps['departure_sec']
    events['previous_departure_trip_id'] = prev_deps['departure_trip_id']
    
    events = events[events['route_arr_id'] != events['route_dep_id']].copy()
    
    print("Applying Phase 2 Metrics Formulas...")
    events['miss_margin_sec'] = events['passenger_ready_sec'] - events['previous_departure_sec']
    events['next_wait_sec'] = events['next_departure_sec'] - events['passenger_ready_sec']
    events['scheduled_headway_sec'] = events['next_departure_sec'] - events['previous_departure_sec']
    
    # Phase 2.1: Wait Fraction
    events['wait_fraction_of_headway'] = calculate_wait_fraction(events['next_wait_sec'], events['scheduled_headway_sec'])
    
    # Phase 2.1: Corrected Near-Miss definition
    events['is_near_miss'] = (
        (events['miss_margin_sec'] > 0) & 
        (events['miss_margin_sec'] <= TransferMetricsConfig.NEAR_MISS_MAX_MARGIN_SEC) & 
        (events['next_wait_sec'] >= TransferMetricsConfig.NEAR_MISS_MIN_WAIT_SEC)
    )
    
    # Phase 2.2: Categorical Severity Levels
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
    
    events = events[final_cols]
    out_file = "artifacts/data/transfer_events.csv"
    events.to_csv(out_file, index=False)
    
    print(f"\n✅ SUCCESS: Phase 2 Metrics Applied to {len(events):,} Events.")
    print(f"   Saved updated schema to: {out_file}")

if __name__ == "__main__":
    generate_transfer_events()
    build_transfer_events()
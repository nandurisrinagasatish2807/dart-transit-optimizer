import pandas as pd
import numpy as np
import os

def time_to_seconds(time_str):
    """
    Phase 5.2 requirement: Converts GTFS HH:MM:SS to total seconds.
    This safely handles >24h times (e.g., 25:30:00 becomes 91800 seconds).
    """
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
        print(f"❌ Error: GTFS files not found in '{raw_dir}/'. Please move them there first.")
        return

    print("Loading GTFS datasets...")
    # Load as strings to preserve IDs exactly (Phase 1.2 requirement)
    stop_times = pd.read_csv(f"{raw_dir}/stop_times.txt", dtype=str)
    trips = pd.read_csv(f"{raw_dir}/trips.txt", dtype=str)
    routes = pd.read_csv(f"{raw_dir}/routes.txt", dtype=str)
    
    print("Joining trips and routes to stop events...")
    # Map trip data
    events = stop_times.merge(trips[['trip_id', 'route_id', 'direction_id', 'service_id']], on='trip_id', how='inner')
    # Map route data
    events = events.merge(routes[['route_id', 'route_short_name']], on='route_id', how='left')
    
    print("Converting GTFS times to absolute seconds (Resolving >24h issues)...")
    events['arrival_sec'] = events['arrival_time'].apply(time_to_seconds)
    events['departure_sec'] = events['departure_time'].apply(time_to_seconds)
    events = events.dropna(subset=['arrival_sec', 'departure_sec'])
    
    # Sort for sequential processing
    print("Sorting events for strict timeline schema...")
    events = events.sort_values(by=['stop_id', 'service_id', 'departure_sec'])
    
    # Export the staging schema
    os.makedirs("artifacts/data", exist_ok=True)
    out_file = "artifacts/data/staged_events.csv"
    events.to_csv(out_file, index=False)
    
    print(f"\n✅ SUCCESS: Formatted {len(events):,} stop events.")
    print(f"   Saved baseline schema to: {out_file}")
    print("   Ready for Phase 1.1 Cross-Join (Arrivals -> Departures).")


def build_transfer_events():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 1.1: Transfer Cross-Join")
    print(f"{'='*50}")
    
    staged_file = "artifacts/data/staged_events.csv"
    if not os.path.exists(staged_file):
        print(f"❌ Error: {staged_file} not found.")
        return

    print("Loading staged events safely...")
    # Load without strict usecols to bypass Pandas C-engine chunking crash
    df = pd.read_csv(staged_file, low_memory=False)
    
    # Enforce numeric types for the time calculations
    df['arrival_sec'] = pd.to_numeric(df['arrival_sec'], errors='coerce')
    df['departure_sec'] = pd.to_numeric(df['departure_sec'], errors='coerce')
    df = df.dropna(subset=['arrival_sec', 'departure_sec'])
    
    # Sort strictly by time for merge_asof
    df = df.sort_values('departure_sec')
    
    walking_time_sec = 120
    
    # Ensure missing string columns (like direction_id) don't break the rename
    for col in ['direction_id', 'route_short_name']:
        if col not in df.columns:
            df[col] = "UNKNOWN"
            
    # Separate arrivals
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

    # Separate departures
    departures = df.rename(columns={
        'trip_id': 'departure_trip_id',
        'route_id': 'route_dep_id',
        'route_short_name': 'route_dep_name',
        'direction_id': 'dir_dep'
    }).drop(columns=['arrival_sec'])

    print("Executing memory-efficient rolling nearest-match (Next Departures)...")
    next_deps = pd.merge_asof(
        arrivals, 
        departures,
        left_on='passenger_ready_sec',
        right_on='departure_sec',
        by=['stop_id', 'service_id'],
        direction='forward',
        suffixes=('', '_drop')
    )
    
    print("Executing memory-efficient rolling nearest-match (Previous Departures)...")
    prev_deps = pd.merge_asof(
        arrivals, 
        departures,
        left_on='passenger_ready_sec',
        right_on='departure_sec',
        by=['stop_id', 'service_id'],
        direction='backward',
        suffixes=('', '_prev')
    )
    
    events = next_deps.copy()
    events['next_departure_sec'] = events['departure_sec']
    events['next_departure_trip_id'] = events['departure_trip_id']
    events['previous_departure_sec'] = prev_deps['departure_sec']
    events['previous_departure_trip_id'] = prev_deps['departure_trip_id']
    
    # Isolate valid transfers
    events = events[events['route_arr_id'] != events['route_dep_id']].copy()
    
    print("Calculating exact wait times and miss margins...")
    events['miss_margin_sec'] = events['passenger_ready_sec'] - events['previous_departure_sec']
    events['next_wait_sec'] = events['next_departure_sec'] - events['passenger_ready_sec']
    events['scheduled_headway_sec'] = events['next_departure_sec'] - events['previous_departure_sec']
    
    # Near-miss constraint formulation
    events['is_near_miss'] = (events['miss_margin_sec'] > 0) & \
                             (events['miss_margin_sec'] <= 180) & \
                             (events['next_wait_sec'] >= 600)
                             
    final_cols = [
        'stop_id', 'service_id', 'arrival_trip_id', 'route_arr_id', 'route_arr_name', 'dir_arr',
        'scheduled_arrival_sec', 'passenger_ready_sec', 'walking_time_sec',
        'route_dep_id', 'route_dep_name', 'dir_dep',
        'previous_departure_trip_id', 'previous_departure_sec',
        'next_departure_trip_id', 'next_departure_sec',
        'miss_margin_sec', 'next_wait_sec', 'scheduled_headway_sec', 'is_near_miss'
    ]
    
    events = events[final_cols]
    out_file = "artifacts/data/transfer_events.csv"
    events.to_csv(out_file, index=False)
    
    print(f"\n✅ SUCCESS: Generated Phase 1 Event Schema.")
    print(f"   Total exact transfer opportunities mapped: {len(events):,}")
    print(f"   Saved to: {out_file}")

# Execution trigger moved to the absolute bottom
if __name__ == "__main__":
    generate_transfer_events()
    build_transfer_events()
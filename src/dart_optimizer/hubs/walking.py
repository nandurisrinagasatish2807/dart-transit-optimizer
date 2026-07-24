import os

import pandas as pd

from dart_optimizer.transfers.metrics import (
    TransferMetricsConfig,
    assign_severity,
    calculate_wait_fraction,
)


def build_hub_transfers():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 3.1: Hub-Level Transfer Matching")
    print(f"{'='*50}")

    staged_file = "artifacts/data/staged_events.csv"
    hubs_file = "artifacts/data/transit_hubs.csv"

    if not os.path.exists(staged_file) or not os.path.exists(hubs_file):
        print("❌ Error: Staged events or transit hubs file missing. Run matcher.py and builder.py first.")
        return

    print("Loading staged events and hub definitions...")
    df = pd.read_csv(staged_file, low_memory=False)
    hubs = pd.read_csv(hubs_file, dtype=str)

    # Force both stop_ids to string to prevent merge type mismatch
    df['stop_id'] = df['stop_id'].astype(str)
    hubs['stop_id'] = hubs['stop_id'].astype(str)

    # Merge hub_id into event dataframe
    df = df.merge(hubs[['stop_id', 'hub_id']], on='stop_id', how='inner')
    df['arrival_sec'] = pd.to_numeric(df['arrival_sec'], errors='coerce')
    df['departure_sec'] = pd.to_numeric(df['departure_sec'], errors='coerce')
    df = df.dropna(subset=['arrival_sec', 'departure_sec']).sort_values('departure_sec')

    walking_time_sec = 120  # Base inter-platform walking time

    for col in ['direction_id', 'route_short_name']:
        if col not in df.columns:
            df[col] = "UNKNOWN"

    print("Separating arrivals and departures by hub...")
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

    print("Executing rolling nearest-match across unified hubs...")
    # Group by hub_id and service_id instead of raw stop_id
    next_deps = pd.merge_asof(
        arrivals, departures,
        left_on='passenger_ready_sec', right_on='departure_sec',
        by=['hub_id', 'service_id'],
        direction='forward', suffixes=('', '_drop')
    )
    
    prev_deps = pd.merge_asof(
        arrivals, departures,
        left_on='passenger_ready_sec', right_on='departure_sec',
        by=['hub_id', 'service_id'],
        direction='backward', suffixes=('', '_prev')
    )

    events = next_deps.copy()
    events['next_departure_sec'] = events['departure_sec']
    events['next_departure_trip_id'] = events['departure_trip_id']
    events['previous_departure_sec'] = prev_deps['departure_sec']
    events['previous_departure_trip_id'] = prev_deps['departure_trip_id']

    # Filter out same-route transfers
    events = events[events['route_arr_id'] != events['route_dep_id']].copy()

    print("Calculating hub-level metrics and severities...")
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

    final_cols = [
        'hub_id', 'stop_id', 'service_id', 'arrival_trip_id', 'route_arr_id', 'route_arr_name', 'dir_arr',
        'scheduled_arrival_sec', 'passenger_ready_sec', 'walking_time_sec',
        'route_dep_id', 'route_dep_name', 'dir_dep',
        'previous_departure_trip_id', 'previous_departure_sec',
        'next_departure_trip_id', 'next_departure_sec',
        'miss_margin_sec', 'next_wait_sec', 'scheduled_headway_sec', 
        'wait_fraction_of_headway', 'severity', 'is_near_miss'
    ]

    events = events[final_cols]
    out_file = "artifacts/data/hub_transfer_events.csv"
    events.to_csv(out_file, index=False)

    print(f"\n✅ SUCCESS: Mapped {len(events):,} hub-level transfer opportunities.")
    print(f"   Saved to: {out_file}")

if __name__ == "__main__":
    build_hub_transfers()
import os

import numpy as np
import pandas as pd

from dart_optimizer.gtfs.calendar import get_active_services
from dart_optimizer.optimizer.blocks import build_block_layovers, evaluate_shift_feasibility
from dart_optimizer.transfers.metrics import TransferMetricsConfig


def time_to_seconds(time_str):
    if pd.isna(time_str): 
        return np.nan
    try:
        h, m, s = map(int, str(time_str).strip().split(':'))
        return h * 3600 + m * 60 + s
    except ValueError:
        return np.nan


def build_network_state(stop_times, trips_routes, hubs):
    """Runs core matching on a given GTFS state to find network-wide near-misses."""
    full_events = stop_times.merge(trips_routes, on='trip_id', how='inner')
    full_events = full_events.merge(hubs[['stop_id', 'hub_id']], on='stop_id', how='inner')
    
    arrivals = full_events[['trip_id', 'route_id', 'route_short_name', 'direction_id', 'stop_id', 'hub_id', 'arrival_sec']].copy()
    arrivals.rename(columns={
        'trip_id': 'arrival_trip_id', 'route_id': 'route_arr_id', 
        'route_short_name': 'route_arr_name', 'direction_id': 'dir_arr', 
        'arrival_sec': 'scheduled_arrival_sec'
    }, inplace=True)
    arrivals['passenger_ready_sec'] = arrivals['scheduled_arrival_sec'] + 120
    
    departures = full_events[['trip_id', 'route_id', 'route_short_name', 'direction_id', 'stop_id', 'hub_id', 'departure_sec']].copy()
    departures.rename(columns={
        'trip_id': 'departure_trip_id', 'route_id': 'route_dep_id', 
        'route_short_name': 'route_dep_name', 'direction_id': 'dir_dep'
    }, inplace=True)
    
    outbound_menu = departures[['hub_id', 'route_dep_id', 'route_dep_name', 'dir_dep']].drop_duplicates()
    arrivals_expanded = arrivals.merge(outbound_menu, on=['hub_id'], how='inner')
    arrivals_expanded = arrivals_expanded[
        (arrivals_expanded['route_arr_id'] != arrivals_expanded['route_dep_id']) | 
        (arrivals_expanded['dir_arr'] != arrivals_expanded['dir_dep'])
    ]
    
    arrivals_expanded = arrivals_expanded.sort_values('passenger_ready_sec').reset_index(drop=True)
    departures = departures.sort_values('departure_sec').reset_index(drop=True)
    match_keys = ['hub_id', 'route_dep_id', 'dir_dep']
    
    deps_lean = departures[['hub_id', 'route_dep_id', 'dir_dep', 'departure_sec', 'departure_trip_id']]
    
    prev_deps = pd.merge_asof(
        arrivals_expanded, deps_lean, 
        left_on='passenger_ready_sec', right_on='departure_sec', 
        by=match_keys, direction='backward'
    )
    next_deps = pd.merge_asof(
        arrivals_expanded, deps_lean, 
        left_on='passenger_ready_sec', right_on='departure_sec', 
        by=match_keys, direction='forward'
    )
    
    events = arrivals_expanded.copy()
    events['previous_departure_trip_id'] = prev_deps['departure_trip_id']
    events['previous_departure_sec'] = prev_deps['departure_sec']
    events['next_departure_sec'] = next_deps['departure_sec']
    
    events = events.dropna(subset=['previous_departure_sec', 'next_departure_sec']).copy()
    events['miss_margin_sec'] = events['passenger_ready_sec'] - events['previous_departure_sec']
    events['next_wait_sec'] = events['next_departure_sec'] - events['passenger_ready_sec']
    
    events['is_near_miss'] = (
        (events['miss_margin_sec'] > 0) & 
        (events['miss_margin_sec'] <= TransferMetricsConfig.NEAR_MISS_MAX_MARGIN_SEC) & 
        (events['next_wait_sec'] >= TransferMetricsConfig.NEAR_MISS_MIN_WAIT_SEC)
    )
    return events


def run_transfer_simulation(target_date_str="20260722"):
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 5: Block-Aware Full-Network Simulator")
    print(f"{'='*50}")
    
    raw_dir = "data/raw" if os.path.exists("data/raw/stop_times.txt") else "."
    
    active_services = get_active_services(target_date_str, gtfs_dir=raw_dir)
    layovers = build_block_layovers(raw_dir=raw_dir)
    
    trips = pd.read_csv(f"{raw_dir}/trips.txt", dtype={'service_id': str, 'trip_id': str, 'route_id': str})
    trips = trips[trips['service_id'].isin(active_services)].copy()
    routes = pd.read_csv(f"{raw_dir}/routes.txt", dtype={'route_id': str})
    trips_routes = trips.merge(routes, on='route_id', how='left')
    
    stop_times = pd.read_csv(f"{raw_dir}/stop_times.txt", dtype={'trip_id': str, 'stop_id': str})
    stop_times['arrival_sec'] = stop_times['arrival_time'].apply(time_to_seconds)
    stop_times['departure_sec'] = stop_times['departure_time'].apply(time_to_seconds)
    stop_times = stop_times.dropna(subset=['arrival_sec', 'departure_sec'])
    
    hubs = pd.read_csv("artifacts/data/transit_hubs.csv", dtype=str)
    
    print("Calculating baseline network state...")
    baseline_events = build_network_state(stop_times, trips_routes, hubs)
    baseline_misses = baseline_events[baseline_events['is_near_miss']].copy()
    
    top_routes = baseline_misses['route_dep_name'].value_counts().head(5).index.tolist()
    offsets = [-180, -120, 60, 120, 180]
    
    simulation_results = []
    print(f"Simulating network ripple effects and operational feasibility for top routes...")
    
    for route in top_routes:
        route_id = trips_routes[trips_routes['route_short_name'] == route]['route_id'].iloc[0]
        # FIX: Grab all trip IDs associated with this route to mask stop_times directly
        route_trip_ids = trips_routes[trips_routes['route_id'] == route_id]['trip_id']
        sample_trip_id = route_trip_ids.iloc[0]

        for offset in offsets:
            feasibility = evaluate_shift_feasibility(layovers, sample_trip_id, offset)
            
            print(f" -> Shifting Route {route} by {offset}s | Block Feasible: {feasibility['block_feasible']}")
            
            shifted_st = stop_times.copy()
            # Apply offset using trip_id instead of route_id
            mask = shifted_st['trip_id'].isin(route_trip_ids)
            shifted_st.loc[mask, 'arrival_sec'] += offset
            shifted_st.loc[mask, 'departure_sec'] += offset
            
            sim_events = build_network_state(shifted_st, trips_routes, hubs)
            sim_misses = sim_events[sim_events['is_near_miss']]
            
            base_grouped = baseline_misses.groupby(['hub_id', 'route_arr_name', 'route_dep_name']).size().reset_index(name='base_misses')
            sim_grouped = sim_misses.groupby(['hub_id', 'route_arr_name', 'route_dep_name']).size().reset_index(name='sim_misses')
            
            comparison = base_grouped.merge(sim_grouped, on=['hub_id', 'route_arr_name', 'route_dep_name'], how='outer').fillna(0)
            comparison['rescued_near_misses'] = comparison['base_misses'] - comparison['sim_misses']
            comparison['newly_created_misses'] = comparison['sim_misses'] - comparison['base_misses']
            
            impacted = comparison[(comparison['rescued_near_misses'] > 0) | (comparison['newly_created_misses'] > 0)].copy()
            
            for _, row in impacted.iterrows():
                simulation_results.append({
                    'hub_id': row['hub_id'],
                    'route_arr_name': row['route_arr_name'],
                    'route_dep_name': row['route_dep_name'],
                    'offset_sec': offset,
                    'offset_min': offset / 60,
                    'rescued_near_misses': max(0, row['rescued_near_misses']),
                    'newly_created_misses': max(0, row['newly_created_misses']),
                    'total_evaluated': row['base_misses'],
                    'block_feasible': feasibility['block_feasible'],
                    'remaining_layover_sec': feasibility['remaining_layover_sec']
                })

    sim_df = pd.DataFrame(simulation_results)
    
    os.makedirs("artifacts/data", exist_ok=True)
    out_file = "artifacts/data/simulation_results.csv"
    sim_df.to_csv(out_file, index=False)
    
    print("\n✅ SUCCESS: Phase 5 Block-Aware Simulation Complete.")
    print(f"   Evaluated cascading network effects and driver layover limits.")
    print(f"   Saved simulation matrix to: {out_file}")

if __name__ == "__main__":
    run_transfer_simulation()
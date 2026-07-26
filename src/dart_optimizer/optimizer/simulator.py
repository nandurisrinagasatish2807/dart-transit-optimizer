import os
import numpy as np
import pandas as pd

from dart_optimizer.gtfs.calendar import get_active_services
from dart_optimizer.optimizer.blocks import build_block_layovers, evaluate_shift_feasibility
from dart_optimizer.transfers.matcher import match_transfers, time_to_seconds

def run_transfer_simulation(target_date_str="20260722"):
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 5: Block-Aware Simulator (Passenger Metrics Update)")
    print(f"{'='*50}")
    
    raw_dir = "data/raw" if os.path.exists("data/raw/stop_times.txt") else "."
    
    active_services = get_active_services(target_date_str, gtfs_dir=raw_dir)
    layovers = build_block_layovers(active_services, raw_dir=raw_dir)
    
    trips = pd.read_csv(f"{raw_dir}/trips.txt", dtype={'service_id': str, 'trip_id': str, 'route_id': str, 'block_id': str})
    if 'direction_id' not in trips.columns: trips['direction_id'] = 0
    trips['direction_id'] = trips['direction_id'].astype(int)
    if 'block_id' not in trips.columns: trips['block_id'] = 'UNKNOWN'
    
    trips = trips[trips['service_id'].isin(active_services)].copy()
    routes = pd.read_csv(f"{raw_dir}/routes.txt", dtype={'route_id': str})
    trips_routes = trips.merge(routes, on='route_id', how='left')
    
    stop_times = pd.read_csv(f"{raw_dir}/stop_times.txt", dtype={'trip_id': str, 'stop_id': str})
    
    for col in ['pickup_type', 'drop_off_type']:
        if col not in stop_times.columns: stop_times[col] = 0
    if 'stop_sequence' not in stop_times.columns: stop_times['stop_sequence'] = 0
        
    stop_times['arrival_sec'] = stop_times['arrival_time'].apply(time_to_seconds)
    stop_times['departure_sec'] = stop_times['departure_time'].apply(time_to_seconds)
    stop_times = stop_times.dropna(subset=['arrival_sec', 'departure_sec'])
    
    hubs = pd.read_csv("artifacts/data/transit_hubs.csv", dtype=str)
    
    print("Calculating baseline network state and passenger wait times...")
    baseline_events = match_transfers(stop_times, trips_routes, hubs=hubs)
    baseline_misses = baseline_events[baseline_events['is_near_miss']].copy()
    
    top_candidates = baseline_misses.groupby(['route_dep_name', 'dir_dep']).size().reset_index(name='misses').sort_values('misses', ascending=False).head(5)
    offsets = [-180, -120, 60, 120, 180]
    
    # FIX: Group total passenger wait times across the entire network, not just the misses
    base_grouped = baseline_events.groupby(['hub_id', 'route_arr_name', 'route_dep_name', 'dir_dep']).agg(
        base_misses=('is_near_miss', 'sum'),
        base_wait_sec=('next_wait_sec', 'sum'),
        total_evaluated=('is_near_miss', 'count')
    ).reset_index()
    
    simulation_results = []
    print(f"Simulating network ripple effects and measuring wait-time trade-offs...")
    
    for _, candidate in top_candidates.iterrows():
        route = candidate['route_dep_name']
        direction = candidate['dir_dep']
        route_id = trips_routes[trips_routes['route_short_name'] == route]['route_id'].iloc[0]
        
        route_trip_ids = trips_routes[(trips_routes['route_id'] == route_id) & (trips_routes['direction_id'] == direction)]['trip_id'].tolist()

        for offset in offsets:
            route_feasible = True
            min_remaining = float('inf')
            violating_trips = 0
            
            for tid in route_trip_ids:
                feas = evaluate_shift_feasibility(layovers, tid, offset)
                if not feas['feasible']:
                    route_feasible = False
                    violating_trips += 1
                if feas['remaining_layover_sec'] is not None:
                    min_remaining = min(min_remaining, feas['remaining_layover_sec'])
            
            if min_remaining == float('inf'):
                min_remaining = None
                
            print(f" -> Shifting Route {route} (Dir {direction}) by {offset}s | Block Feasible: {route_feasible} (Violations: {violating_trips})")
            
            shifted_st = stop_times.copy()
            mask = shifted_st['trip_id'].isin(route_trip_ids)
            shifted_st.loc[mask, 'arrival_sec'] += offset
            shifted_st.loc[mask, 'departure_sec'] += offset
            
            sim_events = match_transfers(shifted_st, trips_routes, hubs=hubs)
            
            # FIX: Calculate simulated wait times
            sim_grouped = sim_events.groupby(['hub_id', 'route_arr_name', 'route_dep_name', 'dir_dep']).agg(
                sim_misses=('is_near_miss', 'sum'),
                sim_wait_sec=('next_wait_sec', 'sum')
            ).reset_index()
            
            comparison = base_grouped.merge(sim_grouped, on=['hub_id', 'route_arr_name', 'route_dep_name', 'dir_dep'], how='outer').fillna(0)
            
            comparison['rescued_near_misses'] = np.maximum(0, comparison['base_misses'] - comparison['sim_misses'])
            comparison['newly_created_misses'] = np.maximum(0, comparison['sim_misses'] - comparison['base_misses'])
            
            # Convert seconds to minutes for clean reporting
            comparison['baseline_total_wait_minutes'] = comparison['base_wait_sec'] / 60.0
            comparison['simulated_total_wait_minutes'] = comparison['sim_wait_sec'] / 60.0
            comparison['wait_minutes_saved'] = np.maximum(0, comparison['baseline_total_wait_minutes'] - comparison['simulated_total_wait_minutes'])
            comparison['wait_minutes_added'] = np.maximum(0, comparison['simulated_total_wait_minutes'] - comparison['baseline_total_wait_minutes'])
            
            # Only record the routes that actually felt the ripple effect
            impacted = comparison[
                (comparison['rescued_near_misses'] > 0) | 
                (comparison['newly_created_misses'] > 0) | 
                (comparison['wait_minutes_saved'] > 0) | 
                (comparison['wait_minutes_added'] > 0)
            ].copy()
            
            for _, row in impacted.iterrows():
                simulation_results.append({
                    'hub_id': row['hub_id'],
                    'route_arr_name': row['route_arr_name'],
                    'route_dep_name': row['route_dep_name'],
                    'direction_id': row['dir_dep'],
                    'offset_sec': offset,
                    'offset_min': offset / 60,
                    'rescued_near_misses': int(row['rescued_near_misses']),
                    'newly_created_misses': int(row['newly_created_misses']),
                    'baseline_total_wait_minutes': round(row['baseline_total_wait_minutes'], 1),
                    'simulated_total_wait_minutes': round(row['simulated_total_wait_minutes'], 1),
                    'wait_minutes_saved': round(row['wait_minutes_saved'], 1),
                    'wait_minutes_added': round(row['wait_minutes_added'], 1),
                    'total_evaluated': int(row['total_evaluated']),
                    'block_feasible': route_feasible,
                    'violating_trips': violating_trips,
                    'min_remaining_layover_sec': min_remaining
                })

    sim_df = pd.DataFrame(simulation_results)
    
    os.makedirs("artifacts/data", exist_ok=True)
    out_file = "artifacts/data/simulation_results.csv"
    sim_df.to_csv(out_file, index=False)
    
    print("\n✅ SUCCESS: Phase 5 Simulation Complete with Passenger Wait-Time Metrics.")
    print(f"   Saved simulation matrix to: {out_file}")

if __name__ == "__main__":
    run_transfer_simulation()
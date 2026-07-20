import pandas as pd

def evaluate_network_transfers(arrivals, departures, min_walk_sec=120):
    print("Aligning physics and directional route pairs (O(n log n) matching)...")
    
    # 1. Apply physical walking time constraints
    arrivals = arrivals.copy()
    arrivals['passenger_ready_sec'] = arrivals['arrival_sec'] + min_walk_sec
    
    # 2. Map valid route directions at each hub to avoid memory-crushing cross joins
    arr_routes = arrivals[['hub_id', 'route_arr', 'dir_arr']].drop_duplicates()
    dep_routes = departures[['hub_id', 'route_dep', 'dir_dep']].drop_duplicates()
    
    # Create all physically possible connection combinations at each hub
    route_pairs = pd.merge(arr_routes, dep_routes, on='hub_id')
    
    # Strictly prevent self-transfers (evaluating a transfer to the exact same route)
    route_pairs = route_pairs[route_pairs['route_arr'] != route_pairs['route_dep']]
    
    # 3. Expand arrival events to seek each specific outbound route direction
    expanded_arrivals = pd.merge(
        arrivals, 
        route_pairs, 
        on=['hub_id', 'route_arr', 'dir_arr']
    )
    
    # 4. Sort arrays strictly by time (Mandatory for merge_asof physics engine)
    expanded_arrivals = expanded_arrivals.sort_values('passenger_ready_sec')
    departures = departures.sort_values('departure_sec')
    
    # 5. Fast-Forward Match: Find the NEXT departing bus for each route pair
    merged_next = pd.merge_asof(
        expanded_arrivals,
        departures,
        left_on='passenger_ready_sec',
        right_on='departure_sec',
        by=['hub_id', 'service_id', 'route_dep', 'dir_dep'],
        direction='forward'
    )
    
    # 6. Rewind Match: Find the PREVIOUS departing bus for each route pair
    merged_prev = pd.merge_asof(
        expanded_arrivals,
        departures,
        left_on='passenger_ready_sec',
        right_on='departure_sec',
        by=['hub_id', 'service_id', 'route_dep', 'dir_dep'],
        direction='backward'
    )
    
    # 7. Assemble the exact transfer gaps
    case_data = merged_next.copy()
    case_data = case_data.rename(columns={'departure_sec': 'departure_sec_next'})
    case_data['departure_sec_prev'] = merged_prev['departure_sec']
    
    # Drop rows where a connection doesn't exist for the rest of the day
    case_data = case_data.dropna(subset=['departure_sec_next', 'departure_sec_prev']).copy()
    
    # 8. Calculate physical wait states
    case_data['previous_departure_gap'] = case_data['passenger_ready_sec'] - case_data['departure_sec_prev']
    case_data['next_departure_wait'] = case_data['departure_sec_next'] - case_data['passenger_ready_sec']
    
    # 9. STRICT FILTER: The missed bus must have departed between 1 second and 5 minutes ago
    is_near_miss = (case_data['previous_departure_gap'] > 0) & (case_data['previous_departure_gap'] <= 300)
    near_misses = case_data[is_near_miss].copy()
    
    # 10. Calculate final objective penalty in minutes
    near_misses['near_miss_penalty'] = (near_misses['next_departure_wait'] - near_misses['previous_departure_gap']) / 60.0
    
    return near_misses
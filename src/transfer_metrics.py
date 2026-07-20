import pandas as pd

def evaluate_network_transfers(arrivals, departures, min_walk_sec=120):
    print("Aligning physics and isolated route pairs...")
    
    # Apply physical walking time
    arrivals = arrivals.copy()
    arrivals['passenger_ready_sec'] = arrivals['time_sec'] + min_walk_sec
    departures = departures.rename(columns={'time_sec': 'departure_sec'})
    
    # Generate all possible connections at each hub
    merged = pd.merge(arrivals, departures, on=['hub_id', 'service_id'])
    
    # Partition conceptually: Ensure passenger isn't transferring to the exact same route
    merged = merged[merged['route_arr'] != merged['route_dep']]
    
    # Constrain memory: Only evaluate departures happening near the arrival window
    valid_window = (merged['departure_sec'] >= merged['passenger_ready_sec'] - 900) & \
                   (merged['departure_sec'] <= merged['passenger_ready_sec'] + 7200)
    merged = merged[valid_window].copy()
    
    # Extract the NEXT departure for EACH specific route pair
    next_deps = merged[merged['departure_sec'] >= merged['passenger_ready_sec']].copy()
    next_deps = next_deps.sort_values('departure_sec').drop_duplicates(
        subset=['hub_id', 'service_id', 'route_arr', 'route_dep', 'passenger_ready_sec'], 
        keep='first'
    )
    
    # Extract the PREVIOUS departure for EACH specific route pair
    prev_deps = merged[merged['departure_sec'] <= merged['passenger_ready_sec']].copy()
    prev_deps = prev_deps.sort_values('departure_sec').drop_duplicates(
        subset=['hub_id', 'service_id', 'route_arr', 'route_dep', 'passenger_ready_sec'], 
        keep='last'
    )
    
    # Combine previous and next logic strictly within the same route pair
    final_transfers = pd.merge(
        next_deps,
        prev_deps[['hub_id', 'service_id', 'route_arr', 'route_dep', 'passenger_ready_sec', 'departure_sec']],
        on=['hub_id', 'service_id', 'route_arr', 'route_dep', 'passenger_ready_sec'],
        how='inner',
        suffixes=('_next', '_prev')
    )
    
    # Calculate exact event gaps
    final_transfers['previous_departure_gap'] = final_transfers['passenger_ready_sec'] - final_transfers['departure_sec_prev']
    final_transfers['next_departure_wait'] = final_transfers['departure_sec_next'] - final_transfers['passenger_ready_sec']
    
    # STRICT FILTER: The missed bus must have departed between 1 second and 5 minutes ago
    is_near_miss = (final_transfers['previous_departure_gap'] > 0) & (final_transfers['previous_departure_gap'] <= 300)
    final_transfers = final_transfers[is_near_miss].copy()
    
    # Calculate the final penalty in minutes
    final_transfers['near_miss_penalty'] = (final_transfers['next_departure_wait'] - final_transfers['previous_departure_gap']) / 60.0
    
    return final_transfers
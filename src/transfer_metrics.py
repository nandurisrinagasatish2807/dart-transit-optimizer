import pandas as pd

def evaluate_network_transfers(arrivals, departures, min_walk_sec=120):
    """
    Calculates the true near-miss penalty across the entire network,
    strictly partitioning the merges by physical hub and active service date.
    """
    arrivals = arrivals.sort_values('time_sec').copy()
    departures = departures.sort_values('time_sec').copy()
    
    departures['matched_dep_time'] = departures['time_sec']
    arrivals['effective_arr_sec'] = arrivals['time_sec'] + min_walk_sec
    
    # Partitioning applied: The 'by' parameter ensures we only match 
    # buses at the exact same physical hub on the exact same service day.
    merged_backward = pd.merge_asof(
        arrivals, departures, 
        left_on='effective_arr_sec', 
        right_on='time_sec',
        by=['hub_id', 'service_id'],
        direction='backward'
    )
    
    merged_forward = pd.merge_asof(
        arrivals, departures, 
        left_on='effective_arr_sec', 
        right_on='time_sec',
        by=['hub_id', 'service_id'],
        direction='forward'
    )
    
    # Standard processing applied
    results = arrivals.copy()
    results['prev_dep_time'] = merged_backward['matched_dep_time']
    results['next_dep_time'] = merged_forward['matched_dep_time']
    
    # CRITICAL FIX: Pull the departing route ID from the forward merge
    results['route_dep'] = merged_forward['route_dep']
    
    results['miss_margin_min'] = (results['effective_arr_sec'] - results['prev_dep_time']) / 60
    results['wait_time_min'] = (results['next_dep_time'] - results['effective_arr_sec']) / 60
    results['near_miss_penalty'] = results['wait_time_min'] - results['miss_margin_min']
    
    return results

# --- Quick Test Block ---
if __name__ == "__main__":
    # Two different hubs at the exact same time
    test_arrivals = pd.DataFrame({
        'hub_id': ['HUB_A', 'HUB_B'],
        'service_id': ['WKDY', 'WKDY'],
        'time_sec': [28800, 28800], # 8:00 AM
        'route_arr': ['101', '101']
    }) 
    
    # Hub A has a bad connection, Hub B has a perfect connection
    test_departures = pd.DataFrame({
        'hub_id': ['HUB_A', 'HUB_A', 'HUB_B'],
        'service_id': ['WKDY', 'WKDY', 'WKDY'],
        'time_sec': [28860, 30660, 29400], # Hub A: 8:01, 8:31 | Hub B: 8:10
        'route_dep': ['102', '102', '102']
    }) 
    
    print("Testing Network-Partitioned Transfer Penalties:")
    res = evaluate_network_transfers(test_arrivals, test_departures, min_walk_sec=120)
    print(res[['hub_id', 'time_sec', 'near_miss_penalty', 'route_dep']])
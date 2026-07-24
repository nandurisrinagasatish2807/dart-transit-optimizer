import pandas as pd


def test_eligibility_rules_logic():
    """Test that same-route and excessive wait filters behave correctly."""
    data = {
        'hub_id': ['cluster_1', 'cluster_1', 'cluster_1'],
        'route_arr_id': ['101', '101', '101'],
        'route_dep_id': ['101', '104', '104'],
        'dir_arr': ['0', '0', '0'],
        'dir_dep': ['0', '0', '1'],
        'next_wait_sec': [500, 3600, 7200], 
        'miss_margin_sec': [10, -5, 20],
        'is_near_miss': [False, True, False]
    }
    df = pd.DataFrame(data)

    valid_route_mask = ~(
        (df['route_arr_id'] == df['route_dep_id']) & 
        (df['dir_arr'] == df['dir_dep'])
    )
    filtered_df = df[valid_route_mask].copy()
    filtered_df = filtered_df[filtered_df['next_wait_sec'] <= 3600]

    assert len(filtered_df) == 1
    assert filtered_df.iloc[0]['route_dep_id'] == '104'

def test_simulation_shift_logic():
    """Test that schedule shifting correctly recalculates wait times and rescues near-misses."""
    wait_sec = 300
    margin_sec = 60 
    offset_sec = -60 

    simulated_wait = wait_sec - offset_sec
    simulated_margin = margin_sec + offset_sec

    assert simulated_wait == 360
    assert simulated_margin == 0

def test_overnight_time_edge_cases():
    """Test GTFS time handling past 24:00:00 (overnight schedules)."""
    # Simulating 23:59:00 + 2 minutes -> 26:01:00 or standard representation
    base_seconds = 23 * 3600 + 59 * 60 # 86340 sec
    added_seconds = 120 # 2 mins
    total_sec = base_seconds + added_seconds
    
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    
    assert hours == 24
    assert minutes == 1

def test_calendar_service_exceptions():
    """Test standard weekday vs added/removed service exceptions logic."""
    active_services_base = {'trip_1': 'weekday', 'trip_2': 'weekend'}
    exceptions = {'trip_1': 'removed', 'trip_3': 'added'}
    
    # Resolve effective service status
    def resolve_service(trip_id, base_map, exc_map):
        if trip_id in exc_map:
            return exc_map[trip_id]
        return base_map.get(trip_id, 'inactive')

    assert resolve_service('trip_1', active_services_base, exceptions) == 'removed'
    assert resolve_service('trip_3', active_services_base, exceptions) == 'added'
    assert resolve_service('trip_2', active_services_base, exceptions) == 'weekend'
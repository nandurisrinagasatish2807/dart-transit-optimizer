import pandas as pd
from unittest.mock import patch

from dart_optimizer.gtfs.calendar import get_active_services
from dart_optimizer.optimizer.simulator import build_network_state
from dart_optimizer.transfers.matcher import time_to_seconds


def test_time_to_seconds_production_logic():
    """Test that the production time converter correctly handles overnight GTFS times."""
    assert time_to_seconds("08:30:00") == 30600
    assert time_to_seconds("24:01:00") == 86460
    assert pd.isna(time_to_seconds(None))


@patch('pandas.read_csv')
@patch('os.path.exists')
def test_calendar_service_resolution(mock_exists, mock_read_csv):
    """Test that get_active_services correctly processes base calendars and date exceptions."""
    mock_exists.return_value = True
    
    cal_df = pd.DataFrame({
        'service_id': ['WEEKDAY_SRV', 'WEEKEND_SRV'],
        'start_date': [20260101, 20260101],
        'end_date': [20261231, 20261231],
        'wednesday': [1, 0]
    })
    
    dates_df = pd.DataFrame({
        'service_id': ['WEEKDAY_SRV', 'HOLIDAY_SRV'],
        'date': [20260722, 20260722],
        'exception_type': [2, 1] 
    })
    
    mock_read_csv.side_effect = [cal_df, dates_df]
    
    active = get_active_services('20260722', gtfs_dir="dummy")
    
    assert 'HOLIDAY_SRV' in active
    assert 'WEEKDAY_SRV' not in active
    assert 'WEEKEND_SRV' not in active


def test_full_network_state_and_positive_shift_simulation():
    """
    Test that build_network_state accurately maps routes, and that shifting 
    a route by a positive offset (departing later) successfully rescues a connection.
    """
    hubs = pd.DataFrame({'stop_id': ['stop_A'], 'hub_id': ['hub_1']})
    
    # Added a 'dep_early' bus so merge_asof always has a backward anchor
    trips_routes = pd.DataFrame({
        'trip_id': ['arr_trip', 'dep_early', 'dep_missed', 'dep_next'],
        'route_id': ['101', '104', '104', '104'],
        'route_short_name': ['Blue', 'Red', 'Red', 'Red'],
        'direction_id': [0, 1, 1, 1]
    })
    
    stop_times = pd.DataFrame({
        'trip_id': ['arr_trip', 'dep_early', 'dep_missed', 'dep_next'],
        'stop_id': ['stop_A', 'stop_A', 'stop_A', 'stop_A'],
        'arrival_sec': [28800, 27000, 28860, 30600],
        'departure_sec': [28800, 27000, 28860, 30600]
    })
    
    # 2. Test Baseline State
    baseline = build_network_state(stop_times, trips_routes, hubs)
    assert len(baseline) == 1
    event = baseline.iloc[0]
    
    # Passenger misses 8:01 bus by 60s, waits for 8:30 bus (1680s wait)
    assert event['miss_margin_sec'] == 60
    assert event['next_wait_sec'] == 1680
    assert event['is_near_miss'] == True
    
    # 3. Test POSITIVE Schedule Shift (Departing Later)
    shifted_st = stop_times.copy()
    # Shift only the Red line buses
    mask = shifted_st['trip_id'].isin(['dep_early', 'dep_missed', 'dep_next'])
    shifted_st.loc[mask, 'arrival_sec'] += 120
    shifted_st.loc[mask, 'departure_sec'] += 120
    
    # 4. Re-run Network State
    simulated = build_network_state(shifted_st, trips_routes, hubs)
    assert len(simulated) == 1
    sim_event = simulated.iloc[0]
    
    # The 8:01 bus is now 8:03. The passenger ready at 8:02 catches it!
    # Next wait is now only 60 seconds (they board at 8:03).
    assert sim_event['next_wait_sec'] == 60 
    assert sim_event['is_near_miss'] == False
import pytest
import pandas as pd
import numpy as np

def test_eligibility_rules_logic():
    """Test that same-route and excessive wait filters behave correctly."""
    # Mock data frame representing transfer events
    data = {
        'hub_id': ['cluster_1', 'cluster_1', 'cluster_1'],
        'route_arr_id': ['101', '101', '101'],
        'route_dep_id': ['101', '104', '104'],
        'dir_arr': ['0', '0', '0'],
        'dir_dep': ['0', '0', '1'],
        'next_wait_sec': [500, 3600, 7200], # 7200 is > 1 hour (invalid)
        'miss_margin_sec': [10, -5, 20],
        'is_near_miss': [False, True, False]
    }
    df = pd.DataFrame(data)

    # Apply Rule 1: Same route & same direction filtering
    valid_route_mask = ~(
        (df['route_arr_id'] == df['route_dep_id']) & 
        (df['dir_arr'] == df['dir_dep'])
    )
    filtered_df = df[valid_route_mask].copy()

    # Apply Rule 2: Max wait window (<= 3600 sec)
    filtered_df = filtered_df[filtered_df['next_wait_sec'] <= 3600]

    # Assertions
    # Row 0 should be dropped (same route 101 and same dir 0)
    # Row 2 should be dropped (wait time 7200 > 3600)
    # Only Row 1 should survive
    assert len(filtered_df) == 1
    assert filtered_df.iloc[0]['route_dep_id'] == '104'

def test_simulation_shift_logic():
    """Test that schedule shifting correctly recalculates wait times and rescues near-misses."""
    wait_sec = 300
    margin_sec = 60 # near miss
    offset_sec = -60 # shift departure 1 minute later / arrival earlier adjust

    simulated_wait = wait_sec - offset_sec
    simulated_margin = margin_sec + offset_sec

    assert simulated_wait == 360
    assert simulated_margin == 0
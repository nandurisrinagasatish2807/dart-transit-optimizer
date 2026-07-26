import numpy as np
import pandas as pd


def time_to_seconds(time_str):
    if pd.isna(time_str): 
        return np.nan
    try:
        h, m, s = map(int, str(time_str).strip().split(':'))
        return h * 3600 + m * 60 + s
    except ValueError:
        return np.nan


def build_block_layovers(active_services, raw_dir="data/raw"):
    """
    Calculates scheduled layovers between date-active trips for each physical bus (block_id).
    """
    import os
    if not os.path.exists(f"{raw_dir}/trips.txt"):
        raw_dir = "."
        
    print("🚌 Analyzing vehicle block constraints and date-active layovers...")
    
    trips_cols = pd.read_csv(f"{raw_dir}/trips.txt", nrows=0).columns
    if 'block_id' not in trips_cols:
        print("⚠️ Warning: block_id not found in trips.txt. Block constraints cannot be evaluated.")
        return pd.DataFrame()
        
    trips = pd.read_csv(f"{raw_dir}/trips.txt", usecols=['trip_id', 'block_id', 'service_id'], dtype=str)
    trips = trips.dropna(subset=['block_id'])
    trips = trips[trips['block_id'].str.strip() != '']
    
    # FIX: Date Filtering - Only sequence trips running on the analysis date
    trips = trips[trips['service_id'].isin(active_services)].copy()
    
    if trips.empty:
        print("⚠️ No valid block_ids populated in active GTFS services. Bypassing constraints.")
        return pd.DataFrame()

    stop_times = pd.read_csv(
        f"{raw_dir}/stop_times.txt", 
        usecols=['trip_id', 'arrival_time', 'departure_time', 'stop_sequence'],
        dtype={'trip_id': str}
    )
    stop_times['arrival_sec'] = stop_times['arrival_time'].apply(time_to_seconds)
    stop_times['departure_sec'] = stop_times['departure_time'].apply(time_to_seconds)
    stop_times = stop_times.dropna(subset=['arrival_sec', 'departure_sec'])

    first_stops = stop_times.loc[stop_times.groupby('trip_id')['stop_sequence'].idxmin()][['trip_id', 'departure_sec']]
    first_stops = first_stops.rename(columns={'departure_sec': 'trip_start_sec'})
    
    last_stops = stop_times.loc[stop_times.groupby('trip_id')['stop_sequence'].idxmax()][['trip_id', 'arrival_sec']]
    last_stops = last_stops.rename(columns={'arrival_sec': 'trip_end_sec'})

    trip_bounds = first_stops.merge(last_stops, on='trip_id')
    trip_bounds = trip_bounds.merge(trips, on='trip_id')

    trip_bounds = trip_bounds.sort_values(['block_id', 'trip_start_sec'])

    # FIX: Validate both incoming and outgoing layovers for the block
    trip_bounds['prev_trip_end_sec'] = trip_bounds.groupby('block_id')['trip_end_sec'].shift(1)
    trip_bounds['next_trip_start_sec'] = trip_bounds.groupby('block_id')['trip_start_sec'].shift(-1)
    
    trip_bounds['incoming_layover_sec'] = trip_bounds['trip_start_sec'] - trip_bounds['prev_trip_end_sec']
    trip_bounds['outgoing_layover_sec'] = trip_bounds['next_trip_start_sec'] - trip_bounds['trip_end_sec']

    layovers = trip_bounds[['block_id', 'trip_id', 'incoming_layover_sec', 'outgoing_layover_sec']].copy()
    
    print(f"✅ Mapped layover constraints for {len(layovers['block_id'].unique())} date-active vehicle blocks.")
    return layovers


def evaluate_shift_feasibility(layovers, trip_id, offset_sec, min_recovery_sec=120):
    """
    Validates if a delay violates outgoing layovers, or if an early departure violates incoming layovers.
    """
    if layovers.empty:
        return {"feasible": True, "remaining_layover_sec": None}
        
    trip_data = layovers[layovers['trip_id'] == trip_id]
    if trip_data.empty:
        return {"feasible": True, "remaining_layover_sec": None}
        
    incoming = trip_data.iloc[0]['incoming_layover_sec']
    outgoing = trip_data.iloc[0]['outgoing_layover_sec']
    
    if offset_sec < 0:
        # Negative shift: Bus leaves earlier, consuming the incoming layover
        if pd.isna(incoming):
            return {"feasible": True, "remaining_layover_sec": None} 
        remaining = incoming + offset_sec 
        return {"feasible": remaining >= min_recovery_sec, "remaining_layover_sec": remaining}
    else:
        # Positive shift: Bus arrives later, consuming the outgoing layover
        if pd.isna(outgoing):
            return {"feasible": True, "remaining_layover_sec": None} 
        remaining = outgoing - offset_sec
        return {"feasible": remaining >= min_recovery_sec, "remaining_layover_sec": remaining}
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


def build_block_layovers(raw_dir="data/raw"):
    """
    Calculates the scheduled layover time between trips for each physical bus (block_id).
    """
    import os
    if not os.path.exists(f"{raw_dir}/trips.txt"):
        raw_dir = "."
        
    print("🚌 Analyzing vehicle block constraints and terminal layovers...")
    
    # 1. Safely load trips and verify block_id exists
    trips_cols = pd.read_csv(f"{raw_dir}/trips.txt", nrows=0).columns
    if 'block_id' not in trips_cols:
        print("⚠️ Warning: block_id not found in trips.txt. Block constraints cannot be evaluated.")
        return pd.DataFrame()
        
    trips = pd.read_csv(f"{raw_dir}/trips.txt", usecols=['trip_id', 'block_id'], dtype=str)
    trips = trips.dropna(subset=['block_id'])
    trips = trips[trips['block_id'].str.strip() != '']
    
    if trips.empty:
        print("⚠️ No valid block_ids populated in GTFS. Block constraints will be bypassed.")
        return pd.DataFrame()

    # 2. Load stop_times to find the start and end of every trip
    # FIX: Force trip_id to be a string so it merges correctly with trips.txt!
    stop_times = pd.read_csv(
        f"{raw_dir}/stop_times.txt", 
        usecols=['trip_id', 'arrival_time', 'departure_time', 'stop_sequence'],
        dtype={'trip_id': str}
    )
    stop_times['arrival_sec'] = stop_times['arrival_time'].apply(time_to_seconds)
    stop_times['departure_sec'] = stop_times['departure_time'].apply(time_to_seconds)
    stop_times = stop_times.dropna(subset=['arrival_sec', 'departure_sec'])

    # 3. Find first and last stop of each trip
    first_stops = stop_times.loc[stop_times.groupby('trip_id')['stop_sequence'].idxmin()][['trip_id', 'departure_sec']]
    first_stops = first_stops.rename(columns={'departure_sec': 'trip_start_sec'})
    
    last_stops = stop_times.loc[stop_times.groupby('trip_id')['stop_sequence'].idxmax()][['trip_id', 'arrival_sec']]
    last_stops = last_stops.rename(columns={'arrival_sec': 'trip_end_sec'})

    trip_bounds = first_stops.merge(last_stops, on='trip_id')
    trip_bounds = trip_bounds.merge(trips, on='trip_id')

    # 4. Sort by physical bus (block_id) and chronological time
    trip_bounds = trip_bounds.sort_values(['block_id', 'trip_start_sec'])

    # 5. Calculate layover to the NEXT trip in the exact same block
    trip_bounds['next_trip_id'] = trip_bounds.groupby('block_id')['trip_id'].shift(-1)
    trip_bounds['next_trip_start_sec'] = trip_bounds.groupby('block_id')['trip_start_sec'].shift(-1)
    
    trip_bounds['scheduled_layover_sec'] = trip_bounds['next_trip_start_sec'] - trip_bounds['trip_end_sec']

    layovers = trip_bounds[['block_id', 'trip_id', 'next_trip_id', 'trip_end_sec', 'next_trip_start_sec', 'scheduled_layover_sec']].copy()
    
    print(f"✅ Mapped layover constraints for {len(layovers['block_id'].unique())} vehicle blocks.")
    return layovers


def evaluate_shift_feasibility(layovers, trip_id, offset_sec, min_recovery_sec=120):
    """
    Determines if a proposed delay consumes too much of the driver's terminal layover.
    Requires a minimum recovery buffer (e.g., 2 minutes) for the driver.
    """
    if layovers.empty:
        return {"block_feasible": True, "remaining_layover_sec": None, "status": "no_block_data"}
        
    trip_data = layovers[layovers['trip_id'] == trip_id]
    if trip_data.empty or pd.isna(trip_data.iloc[0]['next_trip_id']):
        # It is the last trip of the day for this bus, so holding it doesn't delay a subsequent trip
        return {"block_feasible": True, "remaining_layover_sec": None, "status": "end_of_block"}
        
    layover_sec = trip_data.iloc[0]['scheduled_layover_sec']
    
    # If the offset pushes into the layover time, how much break time is left?
    # Positive offset means the bus arrives late to the terminal
    remaining_layover = layover_sec - offset_sec
    
    # A shift is only feasible if the driver still gets their minimum required break
    feasible = remaining_layover >= min_recovery_sec
    
    return {
        "block_feasible": feasible,
        "remaining_layover_sec": remaining_layover,
        "status": "feasible" if feasible else "recovery_violation"
    }

if __name__ == "__main__":
    df = build_block_layovers()
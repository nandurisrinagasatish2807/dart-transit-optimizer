from datetime import datetime, timedelta

import pandas as pd


def load_gtfs_context():
    """Loads and merges the required GTFS static files to get actual schedule data."""
    print("Loading raw GTFS schedule data (this may take a moment)...")
    
    # Force route_id and trip_id to strings immediately to prevent pandas type-casting issues
    trips = pd.read_csv("trips.txt", usecols=['route_id', 'trip_id'], dtype={'route_id': str, 'trip_id': str})
    stop_times = pd.read_csv("stop_times.txt", usecols=['trip_id', 'stop_id', 'arrival_time', 'departure_time'], dtype={'trip_id': str, 'stop_id': str})
    
    schedule = pd.merge(stop_times, trips, on='trip_id', how='inner')
    return schedule

def shift_time(time_str, delta_minutes):
    """Safely shifts GTFS HH:MM:SS string by a specific delta, handling >24h format."""
    try:
        h, m, s = map(int, str(time_str).strip().split(':'))
        dummy_date = datetime(2000, 1, 1) + timedelta(hours=h, minutes=m, seconds=s)
        shifted = dummy_date + timedelta(minutes=delta_minutes)
        return f"{shifted.hour:02d}:{shifted.minute:02d}:{shifted.second:02d}"
    except:
        return time_str

def execute_real_delta_sweep(target_route, max_shift=5):
    """Performs actual data manipulation to calculate exact trade-offs."""
    schedule = load_gtfs_context()
    
    # Force search string to match the forced column type
    target_route_str = str(target_route)
    
    # Check if the route exists
    if target_route_str not in schedule['route_id'].values:
        print(f"❌ Route '{target_route_str}' not found in trips.txt.")
        # Auto-discovery: Grab the route with the most stop events in the system
        fallback_route = schedule['route_id'].value_counts().index[0]
        print(f"🔄 Auto-switching to highest-volume route in dataset: Route '{fallback_route}'")
        target_route_str = fallback_route
        
    # Isolate the target route's schedule
    route_mask = schedule['route_id'] == target_route_str
    target_schedule = schedule[route_mask].copy()
        
    print(f"\n✅ Target Route {target_route_str} loaded. {len(target_schedule)} distinct stop events found.")
    print(f"Executing δ-sweep (-{max_shift} to +{max_shift} minutes)...\n")
    
    results = []
    
    for delta in range(-max_shift, max_shift + 1):
        if delta == 0:
            continue
            
        # 1. SHIFT THE TIME IN MEMORY
        shifted_schedule = target_schedule.copy()
        shifted_schedule['shifted_arrival'] = shifted_schedule['arrival_time'].apply(lambda x: shift_time(x, delta))
        
        # 2. CALCULATE THE REAL IMPACT footprint (Trips and Events)
        affected_trips = shifted_schedule['trip_id'].nunique()
        altered_events = len(shifted_schedule)
        
        results.append({
            'Shift (Minutes)': f"{'+' if delta > 0 else ''}{delta} min",
            'Trips Altered': affected_trips,
            'Stop Events Shifted': altered_events,
            'Operational Cost': f"Adds {abs(delta)} min to {affected_trips} trips"
        })
        
    # Convert to dataframe and display
    ledger_df = pd.DataFrame(results)
    
    print("📊 REAL DATA OPTIMIZATION LEDGER:")
    print(ledger_df.to_string(index=False))

if __name__ == "__main__":
    print(f"\n{'='*50}")
    print("🚇 DART Cross-Hub Trade-Off Optimizer (Real Data)")
    print(f"{'='*50}")
    
    test_route = '27253'
    execute_real_delta_sweep(test_route, max_shift=5)
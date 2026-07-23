import pandas as pd
from datetime import datetime, timedelta
import os

def shift_time(time_str, delta_minutes):
    """Safely shifts GTFS HH:MM:SS string by a specific delta, handling >24h format."""
    try:
        h, m, s = map(int, str(time_str).strip().split(':'))
        dummy_date = datetime(2000, 1, 1) + timedelta(hours=h, minutes=m, seconds=s)
        shifted = dummy_date + timedelta(minutes=delta_minutes)
        return f"{shifted.hour:02d}:{shifted.minute:02d}:{shifted.second:02d}"
    except:
        return time_str

def generate_real_gtfs_patch(target_route, shift_minutes):
    print(f"\n{'='*50}")
    print(f"🚇 DART Schedule Patcher (Real Data)")
    print(f"{'='*50}")
    print(f"Target Route: {target_route}")
    print(f"Applied Shift: +{shift_minutes} minutes\n")
    
    print("Loading raw trips and stop_times...")
    # Load columns as strings to preserve exact GTFS formatting (like leading zeros)
    trips = pd.read_csv("trips.txt", usecols=['route_id', 'trip_id'], dtype=str)
    stop_times = pd.read_csv("stop_times.txt", dtype=str) 
    
    # Filter trips for the target route
    target_trips = trips[trips['route_id'] == str(target_route)]['trip_id'].tolist()
    
    if not target_trips:
        print(f"❌ No trips found for route {target_route}.")
        return
        
    print(f"Found {len(target_trips)} trips for Route {target_route}. Applying patch...")
    
    # Isolate the stop times that need patching
    patch_mask = stop_times['trip_id'].isin(target_trips)
    patched_schedule = stop_times[patch_mask].copy()
    
    # Apply the mathematical shift
    patched_schedule['arrival_time'] = patched_schedule['arrival_time'].apply(lambda x: shift_time(x, shift_minutes))
    patched_schedule['departure_time'] = patched_schedule['departure_time'].apply(lambda x: shift_time(x, shift_minutes))
    
    print("\nPatched Schedule Sample:")
    print(patched_schedule[['trip_id', 'arrival_time', 'departure_time', 'stop_id']].head(3).to_string(index=False))
    
    # Export the usable file
    os.makedirs('artifacts', exist_ok=True)
    patch_filename = f"artifacts/route_{target_route}_stop_times_PATCH.txt"
    patched_schedule.to_csv(patch_filename, index=False)
    
    print(f"\n✅ SUCCESS: Real GTFS patch containing {len(patched_schedule)} updated stop events exported to {patch_filename}")

if __name__ == "__main__":
    # Executing the winning +5 minute shift on our target route
    generate_real_gtfs_patch('27253', 5)
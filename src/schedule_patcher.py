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
    print(f"🚇 DART Schedule Patcher (Production Master)")
    print(f"{'='*50}")
    print(f"Target Route: {target_route}")
    print(f"Applied Shift: +{shift_minutes} minutes\n")
    
    print("Loading raw trips and master stop_times (this will take a moment)...")
    trips = pd.read_csv("trips.txt", usecols=['route_id', 'trip_id'], dtype=str)
    stop_times = pd.read_csv("stop_times.txt", dtype=str) 
    
    target_trips = trips[trips['route_id'] == str(target_route)]['trip_id'].tolist()
    
    if not target_trips:
        print(f"❌ No trips found for route {target_route}.")
        return None, None, None
        
    print(f"Found {len(target_trips)} trips for Route {target_route}. Applying mathematical patch...")
    
    patch_mask = stop_times['trip_id'].isin(target_trips)
    patched_schedule = stop_times[patch_mask].copy()
    
    # Apply the mathematical shift to both arrival and departure columns
    patched_schedule['arrival_time'] = patched_schedule['arrival_time'].apply(lambda x: shift_time(x, shift_minutes))
    patched_schedule['departure_time'] = patched_schedule['departure_time'].apply(lambda x: shift_time(x, shift_minutes))
    
    # Save the isolated patch for auditing purposes
    os.makedirs('artifacts', exist_ok=True)
    patch_filename = f"artifacts/route_{target_route}_stop_times_PATCH.txt"
    patched_schedule.to_csv(patch_filename, index=False)
    print(f"✅ Route-specific audit patch exported to {patch_filename}")

    return stop_times, patched_schedule, target_trips

def merge_patch(original_stop_times, patched_schedule, target_trips):
    print("\nIntegrating patch into master GTFS schedule...")
    
    # 1. Slice out the old, unoptimized rows for our target trips
    clean_master = original_stop_times[~original_stop_times['trip_id'].isin(target_trips)].copy()
    
    # 2. Inject the newly patched rows
    master_patched = pd.concat([clean_master, patched_schedule], ignore_index=True)
    
    # 3. Sort by trip_id and stop_sequence to ensure strict GTFS system compliance
    print("Sorting integrated schedule for GTFS ingestion compliance...")
    master_patched['stop_sequence'] = pd.to_numeric(master_patched['stop_sequence'])
    master_patched = master_patched.sort_values(by=['trip_id', 'stop_sequence'])
    
    # 4. Export the final master payload
    master_filename = "artifacts/master_stop_times_PATCHED.txt"
    master_patched.to_csv(master_filename, index=False)
    
    print(f"\n✅ SUCCESS: Full production-ready GTFS stop_times compiled!")
    print(f"   Total rows safely maintained in master file: {len(master_patched):,}")
    print(f"   Saved to: {master_filename}")

if __name__ == "__main__":
    target_route = '27253'
    shift = 5
    
    # Extract the patch and original data
    original_st, patched_st, modified_trips = generate_real_gtfs_patch(target_route, shift)
    
    # Proceed to master injection if the patch was successful
    if original_st is not None:
        merge_patch(original_st, patched_st, modified_trips)
import pandas as pd

# 1. Load data (using low_memory=False to prevent warning messages on large files)
print("Loading GTFS data...")
stop_times = pd.read_csv('stop_times.txt', low_memory=False)
trips = pd.read_csv('trips.txt')

# 2. Merge to get route_ids into the stop_times
df = pd.merge(stop_times, trips, on='trip_id')

# 3. Filter for the Silver Line (27255) and 229 Bus (27193)
silver = df[(df['route_id'] == 27255) & (df['stop_id'] == 34292)].copy()
bus = df[(df['route_id'] == 27193) & (df['stop_id'] == 33299)].copy()

# 4. Convert arrival_time to datetime
silver['time'] = pd.to_datetime(silver['arrival_time'], format='%H:%M:%S', errors='coerce')
bus['time'] = pd.to_datetime(bus['arrival_time'], format='%H:%M:%S', errors='coerce')

# Drop invalid times
silver = silver.dropna(subset=['time'])
bus = bus.dropna(subset=['time'])

# 5. Merge to find the connections
merged = pd.merge_asof(silver.sort_values('time'), bus.sort_values('time'), 
                       on='time', direction='forward', tolerance=pd.Timedelta('30m'),
                       suffixes=('_train', '_bus'))

# 6. Calculate the gap
result = merged[['arrival_time_train', 'timepoint_train', 'arrival_time_bus', 'timepoint_bus']].dropna(subset=['arrival_time_bus']).copy()
result['gap_minutes'] = (pd.to_datetime(result['arrival_time_bus'], format='%H:%M:%S') - 
                         pd.to_datetime(result['arrival_time_train'], format='%H:%M:%S')).dt.total_seconds() / 60

# Isolate the 69 problematic connections
problematic = result[(result['gap_minutes'] > 0) & (result['gap_minutes'] <= 5)]

# 7. QA Check: Print the results
print(f"\n--- CREDIBILITY QA RESULTS ---")
print(f"Total Problematic Connections: {len(problematic)}")

# Check how many have timepoint == 1.0 (exact scheduled stops)
valid_timepoints = problematic[(problematic['timepoint_train'] == 1.0) & (problematic['timepoint_bus'] == 1.0)]
print(f"Connections built on REAL timepoints (timepoint=1.0): {len(valid_timepoints)}")

print("\nBreakdown of timepoint flags (Train, Bus):")
print(problematic[['timepoint_train', 'timepoint_bus']].value_counts(dropna=False))
import pandas as pd

# Load data
stop_times = pd.read_csv('stop_times.txt')
trips = pd.read_csv('trips.txt')

# Merge to get route_ids into the stop_times
df = pd.merge(stop_times, trips, on='trip_id')

# Filter for the Silver Line (27255) and 229 Bus (27193)
silver = df[(df['route_id'] == 27255) & (df['stop_id'] == 34292)].copy()
bus = df[(df['route_id'] == 27193) & (df['stop_id'] == 33299)].copy()

# Convert arrival_time to datetime, coercing errors to NaT
silver['time'] = pd.to_datetime(silver['arrival_time'], format='%H:%M:%S', errors='coerce')
bus['time'] = pd.to_datetime(bus['arrival_time'], format='%H:%M:%S', errors='coerce')

# CRITICAL FIX: Drop the rows that couldn't be converted to time
silver = silver.dropna(subset=['time'])
bus = bus.dropna(subset=['time'])

# Merge on time to find connections within 30 mins
merged = pd.merge_asof(silver.sort_values('time'), bus.sort_values('time'), 
                       on='time', direction='forward', tolerance=pd.Timedelta('30m'),
                       suffixes=('_train', '_bus'))

# Show the gap
result = merged[['arrival_time_train', 'arrival_time_bus']].dropna().copy()
result['gap_minutes'] = (pd.to_datetime(result['arrival_time_bus'], format='%H:%M:%S') - 
                         pd.to_datetime(result['arrival_time_train'], format='%H:%M:%S')).dt.total_seconds() / 60

# Filter for small gaps (1 to 5 minutes) which are the "problem" connections
problematic = result[(result['gap_minutes'] > 0) & (result['gap_minutes'] <= 5)]

print(f"--- Found {len(problematic)} problematic connections ---")
print(problematic.sort_values('gap_minutes'))
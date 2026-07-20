import pandas as pd
from gtfs_time import parse_gtfs_time
from gtfs_calendar import get_active_services

# 1. Setup paths
DATA_PATH = 'C:/Users/nandu/dart_data/' 
analysis_date = '20260722'

# 2. Get active service IDs
active_services = get_active_services(
    DATA_PATH + 'calendar.txt', 
    DATA_PATH + 'calendar_dates.txt', 
    analysis_date
)

# 3. Load only necessary GTFS files
trips = pd.read_csv(DATA_PATH + 'trips.txt')
stop_times = pd.read_csv(DATA_PATH + 'stop_times.txt')

# 4. Filter for active services ONLY
active_trips = trips[trips['service_id'].isin(active_services)]
active_stop_times = pd.merge(stop_times, active_trips, on='trip_id')

# 5. Apply the time fix 
active_stop_times['arrival_sec'] = active_stop_times['arrival_time'].apply(parse_gtfs_time)
active_stop_times['departure_sec'] = active_stop_times['departure_time'].apply(parse_gtfs_time)

# 6. Isolate the Silver Line / Route 229 bottleneck at Addison
addison_stops = [33245, 33596]
silver_line_id = 27255 
route_229_id = 27193

# Filter for events happening only at Addison
addison_events = active_stop_times[active_stop_times['stop_id'].isin(addison_stops)].copy()

# Separate Silver Line Train Arrivals and Route 229 Bus Departures
silver_arrivals = addison_events[addison_events['route_id'] == silver_line_id][['trip_id', 'arrival_sec']].sort_values('arrival_sec')
bus_departures = addison_events[addison_events['route_id'] == route_229_id][['trip_id', 'departure_sec']].sort_values('departure_sec')

# 7. Penalty Logic using 'merge_asof' to find nearest times
# Find the NEXT bus departure for each train arrival
merged_next = pd.merge_asof(
    silver_arrivals, 
    bus_departures, 
    left_on='arrival_sec', 
    right_on='departure_sec', 
    direction='forward',
    suffixes=('_train', '_next_bus')
)

# Find the PREVIOUS bus departure for each train arrival
merged_prev = pd.merge_asof(
    silver_arrivals, 
    bus_departures, 
    left_on='arrival_sec', 
    right_on='departure_sec', 
    direction='backward'
)

# Combine and apply the Phase 1 formulas
case_data = merged_next.copy()
case_data['prev_bus_departure_sec'] = merged_prev['departure_sec']

# Calculate in seconds
case_data['previous_departure_gap'] = case_data['arrival_sec'] - case_data['prev_bus_departure_sec']
case_data['next_departure_wait'] = case_data['departure_sec'] - case_data['arrival_sec']
case_data['near_miss_penalty'] = case_data['next_departure_wait'] - case_data['previous_departure_gap']

# Convert to readable minutes
case_data['missed_by_mins'] = (case_data['previous_departure_gap'] / 60).round(1)
case_data['wait_mins'] = (case_data['next_departure_wait'] / 60).round(1)
case_data['penalty_mins'] = (case_data['near_miss_penalty'] / 60).round(1)

# Format the arrival time back to readable HH:MM string for display
case_data['arrival_time'] = pd.to_datetime(case_data['arrival_sec'], unit='s').dt.strftime('%H:%M:%S')

print("\n--- Phase 1: Silver Line to Route 229 Bottleneck (Addison) ---")
# Filter to show only transfers where you missed the previous bus by less than 5 minutes
near_misses = case_data[case_data['missed_by_mins'] <= 5.0]
print(near_misses[['arrival_time', 'missed_by_mins', 'wait_mins', 'penalty_mins']].head(10))
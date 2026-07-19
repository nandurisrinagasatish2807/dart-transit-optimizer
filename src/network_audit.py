import pandas as pd
from gtfs_calendar import get_active_services
from gtfs_time import parse_gtfs_time
from transfer_metrics import evaluate_network_transfers

print("1. Resolving Active Services...")
# Using the active Wednesday date we validated earlier
active_services = get_active_services('calendar.txt', 'calendar_dates.txt', '20260722')

print("2. Loading GTFS Data...")
# Loading only the columns we need to aggressively save memory
trips = pd.read_csv('trips.txt', usecols=['trip_id', 'route_id', 'service_id'])
stop_times = pd.read_csv('stop_times.txt', usecols=['trip_id', 'stop_id', 'arrival_time', 'departure_time'])
# Temporarily using stop_name as our physical hub identifier
stops = pd.read_csv('stops.txt', usecols=['stop_id', 'stop_name']) 

# Drop trips that aren't running on this specific Wednesday
active_trips = trips[trips['service_id'].isin(active_services)]

print("3. Merging Schedules and Parsing Times...")
schedule = pd.merge(stop_times, active_trips, on='trip_id')
schedule = pd.merge(schedule, stops, on='stop_id')

# Pass the strings through your custom time parser
schedule['arrival_sec'] = parse_gtfs_time(schedule['arrival_time'])
schedule['departure_sec'] = parse_gtfs_time(schedule['departure_time'])

# Standardize the column names for the transfer metrics engine
arrivals = schedule[['stop_name', 'service_id', 'arrival_sec', 'route_id']].rename(
    columns={'stop_name': 'hub_id', 'arrival_sec': 'time_sec', 'route_id': 'route_arr'}
)
departures = schedule[['stop_name', 'service_id', 'departure_sec', 'route_id']].rename(
    columns={'stop_name': 'hub_id', 'departure_sec': 'time_sec', 'route_id': 'route_dep'}
)

print("4. Calculating Network-Wide Penalties...")
results = evaluate_network_transfers(arrivals, departures, min_walk_sec=120)

print("5. Filtering and Aggregating Worst Transfers...")
# Drop NaN (first trip of the day) and cases where riders wait for the exact same route
valid_transfers = results.dropna(subset=['near_miss_penalty'])
valid_transfers = valid_transfers[valid_transfers['route_arr'] != valid_transfers['route_dep']]
valid_transfers = valid_transfers[valid_transfers['near_miss_penalty'] > 0]

# CRITICAL FIX: Cap the maximum wait penalty at 120 minutes (2 hours)
# This filters out the 29-hour overnight and weekend gaps that skew the dataset
valid_transfers = valid_transfers[valid_transfers['near_miss_penalty'] <= 120]

# Group by Hub to find the worst offenders
worst_hubs = valid_transfers.groupby('hub_id').agg(
    total_failed_connections=('near_miss_penalty', 'count'),
    avg_penalty_minutes=('near_miss_penalty', 'mean'),
    max_penalty_minutes=('near_miss_penalty', 'max')
).reset_index()

# CRITICAL FIX: Filter out statistical noise by requiring at least 10 failures
worst_hubs = worst_hubs[worst_hubs['total_failed_connections'] >= 10]

# Now sort by the highest average penalty
worst_hubs = worst_hubs.sort_values(by='avg_penalty_minutes', ascending=False)

worst_hubs.to_csv('worst_transfers.csv', index=False)
print("Success! A highly defensible worst_transfers.csv has been generated.")
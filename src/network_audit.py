import pandas as pd
from pathlib import Path
from gtfs_calendar import get_active_services
from gtfs_time import parse_gtfs_time
from transfer_metrics import evaluate_network_transfers

# Use relative paths so it works seamlessly on any operating system
DATA_PATH = Path(".")
analysis_date = '20260722'
MIN_WALK_SEC = 120

print("1. Resolving Active Services...")
active_services = get_active_services(
    DATA_PATH / 'calendar.txt', 
    DATA_PATH / 'calendar_dates.txt', 
    analysis_date
)

print("2. Loading GTFS Data...")
trips = pd.read_csv(DATA_PATH / 'trips.txt', usecols=['trip_id', 'route_id', 'service_id'])
stop_times = pd.read_csv(DATA_PATH / 'stop_times.txt', usecols=['trip_id', 'stop_id', 'arrival_time', 'departure_time'])
stops = pd.read_csv(DATA_PATH / 'stops.txt', usecols=['stop_id', 'stop_name']) 

print("3. Merging Schedules and Parsing Times...")
active_trips = trips[trips['service_id'].isin(active_services)]
active_stop_times = pd.merge(stop_times, active_trips, on='trip_id')
active_stop_times = pd.merge(active_stop_times, stops, on='stop_id')
# Temporarily using stop_name as our physical hub identifier
active_stop_times = active_stop_times.rename(columns={'stop_name': 'hub_id'})

active_stop_times['time_sec'] = active_stop_times['arrival_time'].apply(parse_gtfs_time)

# Separate arrivals and departures for the transfer engine
arrivals = active_stop_times[['hub_id', 'service_id', 'route_id', 'time_sec']].rename(columns={'route_id': 'route_arr'})
departures = active_stop_times[['hub_id', 'service_id', 'route_id', 'time_sec']].rename(columns={'route_id': 'route_dep'})

print("4. Calculating Network-Wide Penalties...")
results = evaluate_network_transfers(arrivals, departures, MIN_WALK_SEC)

print("5. Filtering and Aggregating Worst Transfers...")
# Group by hub and calculate metrics to feed the Streamlit dashboard
worst_hubs = results.groupby('hub_id').agg(
    total_failed_connections=('near_miss_penalty', 'count'),
    avg_penalty_minutes=('near_miss_penalty', 'mean'),
    max_penalty_minutes=('near_miss_penalty', 'max')
).reset_index()

# Filter for hubs with at least 10 failures to remove statistical noise
worst_hubs = worst_hubs[worst_hubs['total_failed_connections'] >= 10]
worst_hubs = worst_hubs.sort_values('avg_penalty_minutes', ascending=False)

worst_hubs.to_csv(DATA_PATH / 'worst_transfers.csv', index=False)
print("Success! A highly defensible worst_transfers.csv has been generated.")
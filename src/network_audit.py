import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.cluster import DBSCAN
from gtfs_calendar import get_active_services
from gtfs_time import parse_gtfs_time
from transfer_metrics import evaluate_network_transfers

DATA_PATH = Path(".")
analysis_date = '20260722'
MIN_WALK_SEC = 120

print("1. Resolving Active Services...")
active_services = get_active_services(
    DATA_PATH / 'calendar.txt', 
    DATA_PATH / 'calendar_dates.txt', 
    analysis_date
)

print("2. Loading GTFS Data & Clustering Hubs...")
# Load stops with coordinates for spatial clustering
stops = pd.read_csv(DATA_PATH / 'stops.txt', usecols=['stop_id', 'stop_name', 'stop_lat', 'stop_lon']) 

# Apply DBSCAN to cluster physical platforms within ~200 meters into single hubs
coords = np.radians(stops[['stop_lat', 'stop_lon']].values)
db = DBSCAN(eps=0.0000314, min_samples=1, metric='haversine', algorithm='ball_tree')
stops['hub_id'] = db.fit_predict(coords)

# --- NEW EXPORT LOGIC FOR 3D MAP ---
# Calculate the geographic center of each clustered hub and save it
hub_centroids = stops.groupby('hub_id').agg(
    lat=('stop_lat', 'mean'),
    lon=('stop_lon', 'mean')
).reset_index()
hub_centroids.to_csv(DATA_PATH / 'hub_centroids.csv', index=False)
print(f"Exported coordinates for {len(hub_centroids)} physical hubs to hub_centroids.csv.")
# -----------------------------------

# Load trips with direction_id to prevent transferring to a return trip
trips = pd.read_csv(DATA_PATH / 'trips.txt', usecols=['trip_id', 'route_id', 'service_id', 'direction_id'])
stop_times = pd.read_csv(DATA_PATH / 'stop_times.txt', usecols=['trip_id', 'stop_id', 'arrival_time', 'departure_time'])

print("3. Merging Schedules and Parsing Times...")
active_trips = trips[trips['service_id'].isin(active_services)]
active_stop_times = pd.merge(stop_times, active_trips, on='trip_id')
active_stop_times = pd.merge(active_stop_times, stops, on='stop_id')

# Parse BOTH arrival and departure times
active_stop_times['arrival_sec'] = active_stop_times['arrival_time'].apply(parse_gtfs_time)
active_stop_times['departure_sec'] = active_stop_times['departure_time'].apply(parse_gtfs_time)

# Separate into isolated arrival and departure events
arrivals = active_stop_times[['hub_id', 'service_id', 'route_id', 'direction_id', 'arrival_sec']].rename(
    columns={'route_id': 'route_arr', 'direction_id': 'dir_arr'}
)
departures = active_stop_times[['hub_id', 'service_id', 'route_id', 'direction_id', 'departure_sec']].rename(
    columns={'route_id': 'route_dep', 'direction_id': 'dir_dep'}
)

print("4. Calculating Network-Wide Penalties...")
results = evaluate_network_transfers(arrivals, departures, MIN_WALK_SEC)

print("5. Filtering and Aggregating Worst Transfers...")
# Retain route-pair granularity in the final output as requested by the audit
worst_hubs = results.groupby(['hub_id', 'route_arr', 'route_dep']).agg(
    total_failed_connections=('near_miss_penalty', 'count'),
    avg_penalty_minutes=('near_miss_penalty', 'mean'),
    max_penalty_minutes=('near_miss_penalty', 'max')
).reset_index()

worst_hubs = worst_hubs[worst_hubs['total_failed_connections'] >= 1]
worst_hubs = worst_hubs.sort_values('avg_penalty_minutes', ascending=False)

worst_hubs.to_csv(DATA_PATH / 'worst_transfers.csv', index=False)
print("Success! A highly defensible, route-specific worst_transfers.csv has been generated.")
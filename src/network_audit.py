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
# Dynamically resolve active services using the path object
active_services = get_active_services(
    DATA_PATH / 'calendar.txt', 
    DATA_PATH / 'calendar_dates.txt', 
    analysis_date
)

print("2. Loading GTFS Data...")
# Load GTFS data using the portable path
trips = pd.read_csv(DATA_PATH / 'trips.txt', usecols=['trip_id', 'route_id', 'service_id'])
stop_times = pd.read_csv(DATA_PATH / 'stop_times.txt', usecols=['trip_id', 'stop_id', 'arrival_time', 'departure_time'])
stops = pd.read_csv(DATA_PATH / 'stops.txt', usecols=['stop_id', 'stop_name'])
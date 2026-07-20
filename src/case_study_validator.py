import pandas as pd
from pathlib import Path
from gtfs_time import parse_gtfs_time
from gtfs_calendar import get_active_services

# 1. Use relative paths so it works on any computer
DATA_PATH = Path(".")
analysis_date = '20260722'
MIN_WALK_SEC = 120

print("Loading GTFS data...")
active_services = get_active_services(
    DATA_PATH / 'calendar.txt',
    DATA_PATH / 'calendar_dates.txt',
    analysis_date
)

trips = pd.read_csv(DATA_PATH / 'trips.txt', usecols=['trip_id', 'route_id', 'service_id'])
stop_times = pd.read_csv(DATA_PATH / 'stop_times.txt', usecols=['trip_id', 'stop_id', 'arrival_time', 'departure_time'])

active_trips = trips[trips['service_id'].isin(active_services)]
active_stop_times = pd.merge(stop_times, active_trips, on='trip_id')

active_stop_times['arrival_sec'] = active_stop_times['arrival_time'].apply(parse_gtfs_time)
active_stop_times['departure_sec'] = active_stop_times['departure_time'].apply(parse_gtfs_time)

# 2. Isolate the Silver Line / Route 229 bottleneck at Downtown Carrollton
carrollton_stops = [33245, 33596]
silver_line_id = 27255 
route_229_id = 27193

carrollton_events = active_stop_times[active_stop_times['stop_id'].isin(carrollton_stops)].copy()

silver_arrivals = carrollton_events[carrollton_events['route_id'] == silver_line_id][['trip_id', 'arrival_sec']].sort_values('arrival_sec')
bus_departures = carrollton_events[carrollton_events['route_id'] == route_229_id][['trip_id', 'departure_sec']].sort_values('departure_sec')

# 3. Add Physical Walking Time
silver_arrivals['passenger_ready_sec'] = silver_arrivals['arrival_sec'] + MIN_WALK_SEC

merged_next = pd.merge_asof(
    silver_arrivals, 
    bus_departures, 
    left_on='passenger_ready_sec', 
    right_on='departure_sec', 
    direction='forward',
    suffixes=('_train', '_next_bus')
)

merged_prev = pd.merge_asof(
    silver_arrivals, 
    bus_departures, 
    left_on='passenger_ready_sec', 
    right_on='departure_sec', 
    direction='backward'
)

case_data = merged_next.copy()
case_data['prev_bus_departure_sec'] = merged_prev['departure_sec']

case_data['previous_departure_gap'] = case_data['passenger_ready_sec'] - case_data['prev_bus_departure_sec']
case_data['next_departure_wait'] = case_data['departure_sec'] - case_data['passenger_ready_sec']
case_data['near_miss_penalty'] = case_data['next_departure_wait'] - case_data['previous_departure_gap']

case_data['missed_by_mins'] = (case_data['previous_departure_gap'] / 60).round(1)
case_data['wait_mins'] = (case_data['next_departure_wait'] / 60).round(1)
case_data['penalty_mins'] = (case_data['near_miss_penalty'] / 60).round(1)

case_data['arrival_time'] = pd.to_datetime(case_data['arrival_sec'], unit='s').dt.strftime('%H:%M:%S')

print("\n--- Phase 1: Silver Line to Route 229 Bottleneck (Downtown Carrollton) ---")
near_misses = case_data[case_data['missed_by_mins'].between(0, 5, inclusive='both')]
near_misses = near_misses.dropna(subset=['missed_by_mins', 'wait_mins'])
print(near_misses[['arrival_time', 'missed_by_mins', 'wait_mins', 'penalty_mins']].head(10))
import pandas as pd

DATA_PATH = 'C:/Users/nandu/dart_data/'

print("--- ROUTES MATCHING '229' or 'Silver' ---")
routes = pd.read_csv(DATA_PATH + 'routes.txt')
print(routes[routes['route_short_name'].astype(str).str.contains('229|Silver', case=False, na=False)][['route_id', 'route_short_name', 'route_long_name']])

print("\n--- STOPS MATCHING 'Addison' ---")
stops = pd.read_csv(DATA_PATH + 'stops.txt')
print(stops[stops['stop_name'].astype(str).str.contains('Addison', case=False, na=False)][['stop_id', 'stop_name']])
import pandas as pd

stops = pd.read_csv('stops.txt')

# Let's check our two specific platforms at Downtown Carrollton
our_stops = stops[stops['stop_id'].isin([34292, 33299])]
print("--- DOWNTOWN CARROLLTON STOPS ---")
print(our_stops[['stop_id', 'stop_name', 'parent_station', 'location_type']])

# Let's also see how many total parent stations exist in the network
hubs = stops.dropna(subset=['parent_station'])
print(f"\nTotal stops linked to a parent hub: {len(hubs)}")
print(f"Unique hubs in DART network: {hubs['parent_station'].nunique()}")
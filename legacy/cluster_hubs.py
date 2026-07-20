import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN

print("Loading DART stops...")
stops = pd.read_csv('stops.txt')

# Extract coordinates
coords = stops[['stop_lat', 'stop_lon']].dropna().to_numpy()

# 200 meters in radians for the Haversine formula
# Earth's radius in km is ~6371
kms_per_radian = 6371.0088
epsilon = (200 / 1000) / kms_per_radian 

print("Clustering stops within 200 meters of each other...")
# We use ball_tree algorithm for fast spatial queries
db = DBSCAN(eps=epsilon, min_samples=1, algorithm='ball_tree', metric='haversine').fit(np.radians(coords))

# Assign the generated cluster labels back to our dataframe
stops['hub_id'] = db.labels_

# Let's verify our Downtown Carrollton stops
our_stops = stops[stops['stop_id'].isin([34292, 33299])]
print("\n--- DOWNTOWN CARROLLTON CLUSTER ---")
print(our_stops[['stop_id', 'stop_name', 'hub_id']])

print(f"\nTotal original stops: {len(stops)}")
print(f"Total unique hubs generated: {stops['hub_id'].nunique()}")
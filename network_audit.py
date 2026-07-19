import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import warnings
warnings.filterwarnings('ignore') # Hides Pandas timestamp warnings

print("1. Loading datasets...")
stops = pd.read_csv('stops.txt')
stop_times = pd.read_csv('stop_times.txt', low_memory=False)
trips = pd.read_csv('trips.txt')
routes = pd.read_csv('routes.txt')

print("2. Running Spatial Clustering (Building Hubs)...")
coords = stops[['stop_lat', 'stop_lon']].dropna().to_numpy()
kms_per_radian = 6371.0088
db = DBSCAN(eps=(200/1000)/kms_per_radian, min_samples=1, algorithm='ball_tree', metric='haversine').fit(np.radians(coords))
stops['hub_id'] = db.labels_

print("3. Merging schedules (This takes a moment)...")
df = stop_times.merge(trips, on='trip_id').merge(stops[['stop_id', 'hub_id', 'stop_name']], on='stop_id')
df['time'] = pd.to_datetime(df['arrival_time'], format='%H:%M:%S', errors='coerce')

# THE FIX: Duplicate the time column so it gets suffixed during the merge
df['time_calc'] = df['time'] 
df = df.dropna(subset=['time', 'route_id']).copy()

# Find hubs that have more than 1 route (actual transfer stations)
hub_route_counts = df.groupby('hub_id')['route_id'].nunique()
transfer_hubs = hub_route_counts[hub_route_counts > 1].index.tolist()

# Let's focus on the top 50 busiest hubs to keep processing time reasonable
busiest_hubs = df[df['hub_id'].isin(transfer_hubs)].groupby('hub_id').size().nlargest(50).index.tolist()

print(f"4. Scanning the 50 busiest hubs for bad transfers...")
bad_connections = []

for idx, hub in enumerate(busiest_hubs):
    hub_data = df[df['hub_id'] == hub]
    hub_name = hub_data['stop_name'].iloc[0]
    unique_routes = hub_data['route_id'].unique()
    
    print(f"   Scanning Hub {idx+1}/50: {hub_name} ({len(unique_routes)} routes)")
    
    for route_a in unique_routes:
        for route_b in unique_routes:
            if route_a == route_b:
                continue # Skip transferring to the same route
                
            route_a_data = hub_data[hub_data['route_id'] == route_a].sort_values('time')
            route_b_data = hub_data[hub_data['route_id'] == route_b].sort_values('time')
            
            if route_a_data.empty or route_b_data.empty:
                continue
                
            # Find the connections
            merged = pd.merge_asof(route_a_data, route_b_data, on='time', direction='forward', 
                                   tolerance=pd.Timedelta('30m'), suffixes=('_from', '_to'))
            
            # THE FIX: Use the duplicated time column that successfully split
            merged = merged.dropna(subset=['time_calc_to'])
            merged['gap'] = (merged['time_calc_to'] - merged['time_calc_from']).dt.total_seconds() / 60
            
            # Count connections between 1 and 5 minutes
            bad_count = len(merged[(merged['gap'] > 0) & (merged['gap'] <= 5)])
            
            if bad_count > 0:
                bad_connections.append({
                    'Hub Name': hub_name,
                    'From Route': route_a,
                    'To Route': route_b,
                    'Bad Connections (1-5 min)': bad_count
                })

print("\n5. Aggregating Results...")
results_df = pd.DataFrame(bad_connections)

# Group by Hub and Routes, summing the bad connections
if not results_df.empty:
    final_report = results_df.groupby(['Hub Name', 'From Route', 'To Route']).sum().reset_index()
    final_report = final_report.sort_values(by='Bad Connections (1-5 min)', ascending=False)
    
    # Map Route IDs to real names
    route_map = routes.set_index('route_id')['route_short_name'].to_dict()
    final_report['From Route'] = final_report['From Route'].map(route_map)
    final_report['To Route'] = final_report['To Route'].map(route_map)
    
    # Save to CSV
    final_report.to_csv('worst_transfers.csv', index=False)
    
    print("\n--- TOP 10 WORST TRANSFERS IN DALLAS ---")
    print(final_report.head(10).to_string(index=False))
    print("\n✅ Full report saved to 'worst_transfers.csv'!")
else:
    print("No bad connections found in this pass.")
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

print("1. Loading datasets...")
stop_times = pd.read_csv('stop_times.txt', low_memory=False)
trips = pd.read_csv('trips.txt')
routes = pd.read_csv('routes.txt')
stops = pd.read_csv('stops.txt')

routes['route_short_name'] = routes['route_short_name'].astype(str).str.strip().str.replace('.0', '', regex=False)

print("2. Rebuilding Hubs (Spatial Clustering)...")
coords = stops[['stop_lat', 'stop_lon']].dropna().to_numpy()
kms_per_radian = 6371.0088
db = DBSCAN(eps=(200/1000)/kms_per_radian, min_samples=1, algorithm='ball_tree', metric='haversine').fit(np.radians(coords))
stops['hub_id'] = db.labels_

print("3. Merging schedules to find the intersection...")
# Ensure we bring in direction_id from trips
df = stop_times.merge(trips[['trip_id', 'route_id', 'service_id', 'direction_id']], on='trip_id')
df = df.merge(stops[['stop_id', 'hub_id', 'stop_name']], on='stop_id')
df = df.merge(routes[['route_id', 'route_short_name']], on='route_id')

df['time'] = pd.to_datetime(df['arrival_time'], format='%H:%M:%S', errors='coerce')
df = df.dropna(subset=['time', 'route_id', 'direction_id']).copy()

# FILTER TO STANDARD WEEKDAY (Solves the 0-minute overlap trap)
dominant_service = df['service_id'].value_counts().idxmax()
print(f"   -> Filtering to standard weekday (Service ID: {dominant_service})")
df = df[df['service_id'] == dominant_service].copy()

# FIND THE TARGET HUB
hub_routes = df.groupby('hub_id')['route_short_name'].unique()
target_hub = None
for hub_id, r_list in hub_routes.items():
    if '106' in r_list and '128' in r_list:
        target_hub = hub_id
        break

df_hub = df[df['hub_id'] == target_hub].copy()
coupled_routes = ['106', '128', '101', '102', '219']
df_coupled = df_hub[df_hub['route_short_name'].isin(coupled_routes)].copy()

# Extract unique (route, direction) tuples
route_dirs = df_coupled[['route_short_name', 'direction_id']].drop_duplicates().values

print("\n--- STEP 1: VERIFYING DIRECTIONAL HEADWAYS ---")
headways = {}
for r, d in route_dirs:
    r_data = df_coupled[(df_coupled['route_short_name'] == r) & (df_coupled['direction_id'] == d)].sort_values('time')
    hw = r_data['time'].diff().dt.total_seconds().median() / 60
    # Fallback to 30 mins if only one bus exists in that direction
    hw = hw if pd.notna(hw) and hw > 0 else 30.0 
    headways[(r, d)] = hw
    print(f"Route {r} (Dir {d}) Median Headway: {hw:.1f} minutes")

print("\n--- STEP 2: RUNNING TIER 1 OPTIMIZATION SWEEP ---")
print("Applying shift globally to Route 128 (locking directions)...")

def evaluate_shift(df_base, target_route, shift_minutes):
    test_df = df_base.copy()
    
    # TIER 1 LOGIC: Apply the shift to the entire route (both directions)
    mask = test_df['route_short_name'] == target_route
    test_df.loc[mask, 'time'] = test_df.loc[mask, 'time'] + pd.Timedelta(minutes=shift_minutes)
    test_df['time_calc'] = test_df['time'] 
    
    total_bad = 0
    total_penalty = 0
    walk_time = 2.0 
    
    # TIER 1 EVALUATION: Loop through directional tuples
    for r_from, d_from in route_dirs:
        for r_to, d_to in route_dirs:
            if r_from == r_to: continue # Skip same-route transfers
            
            df_from = test_df[(test_df['route_short_name'] == r_from) & (test_df['direction_id'] == d_from)].sort_values('time')
            df_to = test_df[(test_df['route_short_name'] == r_to) & (test_df['direction_id'] == d_to)].sort_values('time')
            
            if df_from.empty or df_to.empty: continue
            
            merged = pd.merge_asof(df_from, df_to, on='time', direction='forward', tolerance=pd.Timedelta('45m'), suffixes=('_from', '_to'))
            merged = merged.dropna(subset=['time_calc_to'])
            merged['gap'] = (merged['time_calc_to'] - merged['time_calc_from']).dt.total_seconds() / 60
            
            # Metric 1: Bad Connections
            bad_count = len(merged[(merged['gap'] > 0) & (merged['gap'] <= 5)])
            total_bad += bad_count
            
            # Metric 2: Rider Penalty
            valid_transfers = merged[(merged['gap'] > 0) & (merged['gap'] <= 45)].copy()
            if not valid_transfers.empty:
                missed = valid_transfers['gap'] < walk_time
                valid_transfers.loc[missed, 'penalty'] = valid_transfers['gap'] + headways[(r_to, d_to)]
                valid_transfers.loc[~missed, 'penalty'] = valid_transfers['gap']
                total_penalty += valid_transfers['penalty'].sum()
                
    return total_bad, total_penalty

shifts = list(range(-10, 11))
bad_results = []
penalty_results = []

for s in shifts:
    bad, penalty = evaluate_shift(df_coupled, '128', s)
    bad_results.append(bad)
    penalty_results.append(penalty)
    print(f"Shift {s:+3d}m | Bad Conns: {bad:3d} | Rider-Mins Lost: {penalty:,.0f}")

print("\n--- STEP 3: GENERATING TIER 1 DUAL-AXIS CHART ---")
fig, ax1 = plt.subplots(figsize=(10, 6))

color1 = '#2c3e50'
ax1.set_xlabel('Offset Applied to Route 128 (Minutes)', fontsize=12)
ax1.set_ylabel('Total Bad Connections (1-5 min)', color=color1, fontsize=12)
ax1.plot(shifts, bad_results, marker='o', color=color1, linewidth=2, label="Bad Connections")
ax1.tick_params(axis='y', labelcolor=color1)
ax1.grid(True, alpha=0.3)
ax1.set_xticks(shifts)

ax2 = ax1.twinx()
color2 = '#e67e22'
ax2.set_ylabel('Total Rider-Minutes Lost', color=color2, fontsize=12)
ax2.plot(shifts, penalty_results, marker='s', linestyle='--', color=color2, linewidth=2, label="Rider Penalty (Wait + Missed Headway)")
ax2.tick_params(axis='y', labelcolor=color2)

# Disclaimer added to chart title per Claude's feedback
plt.title("Tier 1 Route Optimization: Hampton @ Singleton (Locked Directions)\n*Assuming uniform boarding demand (GTFS limitation)", fontsize=13, fontweight='bold')
fig.tight_layout()

plt.savefig('optimization_tier1.png', dpi=300, bbox_inches='tight')
print("✅ Saved chart as 'optimization_tier1.png'")
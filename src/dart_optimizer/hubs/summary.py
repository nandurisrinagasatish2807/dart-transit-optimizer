import pandas as pd
import numpy as np
import os

def generate_hub_summary():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 3.3: Hub-Level Summary")
    print(f"{'='*50}")

    events_file = "artifacts/data/hub_transfer_events.csv"
    if not os.path.exists(events_file):
        print(f"❌ Error: {events_file} not found. Run walking.py first.")
        return

    print("Loading hub-level transfer events...")
    df = pd.read_csv(events_file, dtype=str)
    
    # Safely parse string booleans and numbers
    df['is_near_miss'] = df['is_near_miss'].astype(str).str.lower() == 'true'
    df['is_near_miss'] = df['is_near_miss'].astype(int)
    
    df['next_wait_sec'] = pd.to_numeric(df['next_wait_sec'], errors='coerce')
    df['is_successful'] = (df['is_near_miss'] == 0) & (df['next_wait_sec'] < 1200)

    print("Aggregating metrics by hub and route pair...")
    groupby_cols = ['hub_id', 'route_arr_id', 'route_arr_name', 'route_dep_id', 'route_dep_name', 'dir_arr', 'dir_dep']

    summary = df.groupby(groupby_cols).agg(
        transfer_opportunities=('arrival_trip_id', 'count'),
        successful_transfers=('is_successful', 'sum'),
        near_misses=('is_near_miss', 'sum'),
        median_transfer_wait_sec=('next_wait_sec', 'median'),
        p90_transfer_wait_sec=('next_wait_sec', lambda x: x.quantile(0.90)),
        max_transfer_wait_sec=('next_wait_sec', 'max')
    ).reset_index()

    print("Calculating rates and converting metrics to minutes...")
    summary['near_miss_rate'] = (summary['near_misses'] / summary['transfer_opportunities']).round(3)
    summary['median_transfer_wait_minutes'] = (summary['median_transfer_wait_sec'] / 60).round(1)
    summary['p90_transfer_wait_minutes'] = (summary['p90_transfer_wait_sec'] / 60).round(1)

    final_cols = [
        'hub_id', 'route_arr_id', 'route_arr_name', 'route_dep_id', 'route_dep_name', 'dir_arr', 'dir_dep',
        'transfer_opportunities', 'successful_transfers', 'near_misses', 'near_miss_rate',
        'median_transfer_wait_minutes', 'p90_transfer_wait_minutes'
    ]
    
    summary = summary[final_cols].sort_values(by=['near_misses', 'near_miss_rate'], ascending=[False, False])

    out_file = "artifacts/data/hub_transfer_summary.csv"
    summary.to_csv(out_file, index=False)

    print(f"\n✅ SUCCESS: Generated Phase 3 Hub Summary Output.")
    print(f"   Total unique hub-level route pairs mapped: {len(summary):,}")
    print(f"   Saved to: {out_file}")

if __name__ == "__main__":
    generate_hub_summary()
import os

import pandas as pd


def generate_summary():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 2.3: Corrected Transfer Summary")
    print(f"{'='*50}")

    events_file = "artifacts/data/transfer_events.csv"
    if not os.path.exists(events_file):
        print(f"❌ Error: {events_file} not found. Run matcher.py first.")
        return

    print("Loading event-level transfer data with Phase 2 metrics...")
    df = pd.read_csv(events_file)

    df['is_near_miss'] = df['is_near_miss'].astype(int)
    
    # Define successful transfers (events that are not near misses and have acceptable wait times)
    df['is_successful'] = (df['is_near_miss'] == 0) & (df['next_wait_sec'] < 1200)

    print("Aggregating network metrics by stop and route pair...")
    groupby_cols = ['stop_id', 'route_arr_id', 'route_arr_name', 'route_dep_id', 'route_dep_name', 'dir_arr', 'dir_dep']

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

    # Clean up columns for final Phase 2 summary schema
    final_cols = [
        'stop_id', 'route_arr_id', 'route_arr_name', 'route_dep_id', 'route_dep_name', 'dir_arr', 'dir_dep',
        'transfer_opportunities', 'successful_transfers', 'near_misses', 'near_miss_rate',
        'median_transfer_wait_minutes', 'p90_transfer_wait_minutes'
    ]
    
    summary = summary[final_cols].sort_values(by=['near_misses', 'near_miss_rate'], ascending=[False, False])

    out_file = "artifacts/data/transfer_summary.csv"
    summary.to_csv(out_file, index=False)

    print("\n✅ SUCCESS: Generated Phase 2 Transfer Summary.")
    print(f"   Total route pairs analyzed: {len(summary):,}")
    print(f"   Saved to: {out_file}")

if __name__ == "__main__":
    generate_summary()
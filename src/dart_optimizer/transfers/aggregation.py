import pandas as pd
import numpy as np
import os

def generate_summary():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 1.3: Transfer Summary")
    print(f"{'='*50}")

    events_file = "artifacts/data/transfer_events.csv"
    if not os.path.exists(events_file):
        print(f"❌ Error: {events_file} not found. Run matcher.py first.")
        return

    print("Loading event-level transfer data...")
    df = pd.read_csv(events_file)

    # Convert boolean near-misses to integers for easy summing
    df['is_near_miss'] = df['is_near_miss'].astype(int)

    print("Aggregating metrics by stop and route pair...")
    # Using stop_id as the Phase 1 proxy for hub_id
    groupby_cols = ['stop_id', 'route_arr_id', 'route_dep_id', 'dir_arr', 'dir_dep']

    # Execute the aggregation math
    summary = df.groupby(groupby_cols).agg(
        transfer_events=('arrival_trip_id', 'count'),
        near_miss_count=('is_near_miss', 'sum'),
        median_miss_margin_sec=('miss_margin_sec', 'median'),
        median_next_wait_sec=('next_wait_sec', 'median'),
        p90_next_wait_sec=('next_wait_sec', lambda x: x.quantile(0.90)),
        maximum_next_wait_sec=('next_wait_sec', 'max')
    ).reset_index()

    print("Calculating network rates (Seconds -> Minutes)...")
    summary['near_miss_rate'] = (summary['near_miss_count'] / summary['transfer_events']).round(3)

    summary['median_miss_margin_minutes'] = (summary['median_miss_margin_sec'] / 60).round(1)
    summary['median_next_wait_minutes'] = (summary['median_next_wait_sec'] / 60).round(1)
    summary['p90_next_wait_minutes'] = (summary['p90_next_wait_sec'] / 60).round(1)
    summary['maximum_next_wait_minutes'] = (summary['maximum_next_wait_sec'] / 60).round(1)

    # Filter down to the strict Phase 1.3 roadmap columns
    final_cols = [
        'stop_id', 'route_arr_id', 'route_dep_id', 'dir_arr', 'dir_dep',
        'transfer_events', 'near_miss_count', 'near_miss_rate',
        'median_miss_margin_minutes', 'median_next_wait_minutes',
        'p90_next_wait_minutes', 'maximum_next_wait_minutes'
    ]
    summary = summary[final_cols]

    # Sort to float the absolute worst bottlenecks to the very top
    summary = summary.sort_values(by=['near_miss_count', 'near_miss_rate'], ascending=[False, False])

    out_file = "artifacts/data/transfer_summary.csv"
    summary.to_csv(out_file, index=False)

    print(f"\n✅ SUCCESS: Generated Phase 1.3 Summary Output.")
    print(f"   Total unique route-pair transfer bottlenecks mapped: {len(summary):,}")
    print(f"   Saved to: {out_file}")

if __name__ == "__main__":
    generate_summary()
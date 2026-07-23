import pandas as pd
import numpy as np
import os

def apply_eligibility_rules():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 4: Passenger Eligibility Filters")
    print(f"{'='*50}")

    events_file = "artifacts/data/hub_transfer_events.csv"
    if not os.path.exists(events_file):
        print(f"❌ Error: {events_file} not found. Run walking.py first.")
        return

    print("Loading hub-level transfer events...")
    df = pd.read_csv(events_file, low_memory=False)
    
    initial_count = len(df)
    print(f"Initial raw transfer opportunities: {initial_count:,}")

    # Ensure numeric columns
    df['next_wait_sec'] = pd.to_numeric(df['next_wait_sec'], errors='coerce')
    df['miss_margin_sec'] = pd.to_numeric(df['miss_margin_sec'], errors='coerce')

    print("Applying Rule 1: Filtering out same-route and same-direction transfers...")
    # Passengers don't 'transfer' from Route 3 to Route 3 in the same direction at the same stop
    valid_route_mask = ~(
        (df['route_arr_id'] == df['route_dep_id']) & 
        (df['dir_arr'] == df['dir_dep'])
    )
    df = df[valid_route_mask].copy()

    print("Applying Rule 2: Enforcing maximum viable transfer wait window (<= 60 minutes)...")
    # Waiting more than 1 hour for a transfer invalidates it as a practical connection
    MAX_VIABLE_WAIT_SEC = 3600
    df = df[df['next_wait_sec'] <= MAX_VIABLE_WAIT_SEC].copy()

    print("Applying Rule 3: Removing negative or impossible wait times...")
    df = df[df['next_wait_sec'] >= 0].copy()

    final_count = len(df)
    filtered_out = initial_count - final_count

    out_file = "artifacts/data/eligible_transfer_events.csv"
    df.to_csv(out_file, index=False)

    print(f"\n✅ SUCCESS: Eligibility Rules Applied.")
    print(f"   Filtered out invalid/unrealistic transfers: {filtered_out:,}")
    print(f"   Final valid passenger transfer opportunities: {final_count:,}")
    print(f"   Saved to: {out_file}")

if __name__ == "__main__":
    apply_eligibility_rules()
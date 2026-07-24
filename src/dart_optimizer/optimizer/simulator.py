import os

import pandas as pd


def run_transfer_simulation():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 5: Transfer Optimization Simulator (Sign Corrected)")
    print(f"{'='*50}")

    eligible_file = "artifacts/data/eligible_transfer_events.csv"
    if not os.path.exists(eligible_file):
        print("❌ No near-misses found to optimize.")
        return

    # FIX 1: Actually load the dataset!
    bottlenecks = pd.read_csv(eligible_file)

    if bottlenecks.empty:
        print("❌ Dataset is empty.")
        return

    # Define optimization offset range in seconds (shifting departure times from -300s to +300s)
    # Positive shift = departing later (closes the miss margin gap)
    offset_range_sec = [-300, -240, -180, -120, -60, 0, 60, 120, 180, 240, 300]
    
    print(f"Simulating schedule offsets ({[o // 60 for o in offset_range_sec]} minutes) on bottleneck pairs...")

    simulation_results = []

    # Group by hub and route pair to evaluate localized shift impacts
    grouped = bottlenecks.groupby(['hub_id', 'route_arr_name', 'route_dep_name'])

    for name, group in grouped:
        hub_id, arr_route, dep_route = name
        
        for offset in offset_range_sec:
            # FIX 2: Correct Algebraic Signs!
            # If a bus departs later (+ offset), the wait for the next bus is shorter
            simulated_wait = group['next_wait_sec'] - offset
            
            # If a bus departs later (+ offset), the miss margin (gap to catch it) DECREASES
            simulated_margin = group['miss_margin_sec'] - offset
            
            # Re-evaluate near-miss condition under the simulated offset
            # A successful rescue means the miss margin is eliminated (<= 0) while keeping wait time viable
            rescued = (simulated_margin <= 0) & (simulated_wait >= 0) & (simulated_wait <= 1200)
            
            rescued_count = rescued.sum()
            
            simulation_results.append({
                'hub_id': hub_id,
                'route_arr_name': arr_route,
                'route_dep_name': dep_route,
                'offset_sec': offset,
                'offset_min': offset / 60,
                'rescued_near_misses': rescued_count,
                'total_evaluated': len(group)
            })

    sim_df = pd.DataFrame(simulation_results)
    
    os.makedirs("artifacts/data", exist_ok=True)
    out_file = "artifacts/data/simulation_results.csv"
    sim_df.to_csv(out_file, index=False)

    print("\n✅ SUCCESS: Phase 5 Simulation Complete.")
    print(f"   Evaluated {len(sim_df):,} shift scenarios across bottleneck hub pairs.")
    print(f"   Saved simulation matrix to: {out_file}")

if __name__ == "__main__":
    run_transfer_simulation()
import pandas as pd
import numpy as np
import os

def generate_recommendations():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 5.2: Optimal Schedule Recommendations")
    print(f"{'='*50}")

    sim_file = "artifacts/data/simulation_results.csv"
    if not os.path.exists(sim_file):
        print(f"❌ Error: {sim_file} not found. Run simulator.py first.")
        return

    print("Loading simulation results matrix...")
    sim_df = pd.read_csv(sim_file)

    if len(sim_df) == 0:
        print("⚠️ Simulation results are empty.")
        return

    print("Determining optimal schedule shifts per hub and route pair...")
    
    # We want to find the offset that maximizes 'rescued_near_misses' for each pair
    # If there's a tie, prefer 0 shift or the smallest absolute shift to minimize schedule disruption
    sim_df['abs_offset'] = sim_df['offset_min'].abs()
    
    # Sort by rescued near-misses (descending) and absolute offset (ascending)
    sorted_sim = sim_df.sort_values(
        by=['hub_id', 'route_arr_name', 'route_dep_name', 'rescued_near_misses', 'abs_offset'],
        ascending=[True, True, True, False, True]
    )

    # Drop duplicates to keep the best single offset per hub/route pair
    optimal_df = sorted_sim.drop_duplicates(
        subset=['hub_id', 'route_arr_name', 'route_dep_name'],
        keep='first'
    ).copy()

    # Filter out recommendations where zero near-misses were rescued
    optimal_df = optimal_df[optimal_df['rescued_near_misses'] > 0].sort_values(
        by='rescued_near_misses', ascending=False
    )

    final_cols = [
        'hub_id', 'route_arr_name', 'route_dep_name',
        'offset_min', 'rescued_near_misses', 'total_evaluated'
    ]
    
    optimal_df = optimal_df[final_cols]
    
    out_file = "artifacts/data/optimal_schedule_recommendations.csv"
    optimal_df.to_csv(out_file, index=False)

    print(f"\n✅ SUCCESS: Generated Optimal Schedule Recommendations.")
    print(f"   Total high-impact bottleneck pairs optimized: {len(optimal_df):,}")
    print(f"   Top recommended adjustments saved to: {out_file}")

if __name__ == "__main__":
    generate_recommendations()
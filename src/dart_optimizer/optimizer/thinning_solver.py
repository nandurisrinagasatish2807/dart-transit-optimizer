import os
import pandas as pd

def solve_corridor_thinning():
    print("==================================================")
    print("✂️ DART Optimizer | Greedy Corridor Thinning Solver")
    print("==================================================")

    df = pd.read_csv("artifacts/data/downtown_corridor_thinning.csv")
    
    # Filter for tight pairs under 100m where consolidation has the highest operational impact
    tight_pairs = df[df["effective_distance_m"] <= 100.0].copy()
    
    print(f"Analyzing {len(tight_pairs)} tight corridor segments (≤100m) for automated thinning...")

    recommendations = []
    for _, r in tight_pairs.iterrows():
        # Heuristic: If distance < 75m and weekday trips > 50, flag as high-priority removal candidate
        priority = "High" if r["effective_distance_m"] < 75.0 and r["weekday_trips"] > 50 else "Moderate"
        recommendations.append({
            "Corridor / Routes": f"Rts: {r['routes']}",
            "Stop A (Keep)": r["from_stop_name"],
            "Stop B (Review Removal)": r["to_stop_name"],
            "Spacing (m)": r["effective_distance_m"],
            "Weekday Trips": r["weekday_trips"],
            "Priority": priority,
        })

    rec_df = pd.DataFrame(recommendations).sort_values(["Priority", "Spacing (m)"], ascending=[False, True])
    out_path = "artifacts/data/downtown_thinning_recommendations.csv"
    rec_df.to_csv(out_path, index=False)
    print(f"✅ Generated {len(rec_df)} actionable stop review recommendations. Saved to {out_path}")
    print(rec_df.to_string(index=False))

if __name__ == "__main__":
    solve_corridor_thinning()
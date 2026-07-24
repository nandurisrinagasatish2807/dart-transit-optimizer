import os

import pandas as pd


def generate_executive_report():
    print(f"\n{'='*50}")
    print("🚇 DART Optimizer | Phase 7: Executive Reporting & Export")
    print(f"{'='*50}")

    summary_file = "artifacts/data/eligible_transfer_summary.csv"
    recs_file = "artifacts/data/optimal_schedule_recommendations.csv"

    if not os.path.exists(summary_file) or not os.path.exists(recs_file):
        print("❌ Error: Required summary or recommendation files missing. Run previous phases first.")
        return

    print("Compiling network intelligence metrics...")
    summary_df = pd.read_csv(summary_file)
    recs_df = pd.read_csv(recs_file)

    total_pairs = len(summary_df)
    total_near_misses = summary_df['near_misses'].sum()
    avg_near_miss_rate = summary_df['near_miss_rate'].mean() * 100
    optimized_pairs = len(recs_df)
    total_rescued = recs_df['rescued_near_misses'].sum()

    report_content = f"""
==================================================
🚇 DART TRANSIT TRANSFER OPTIMIZER: EXECUTIVE REPORT
==================================================

1. NETWORK OVERVIEW & SCOPE
   - Total Unique Hub Route Pairs Mapped: {total_pairs:,}
   - Total Near-Miss Transfer Events Tracked: {total_near_misses:,}
   - Network Average Near-Miss Rate: {avg_near_miss_rate:.2f}%

2. OPTIMIZATION SIMULATION RESULTS (PHASE 5)
   - High-Impact Bottleneck Pairs Optimized: {optimized_pairs:,}
   - Total Near-Misses Rescued via Schedule Shifting: {total_rescued:,}

3. TOP 5 CRITICAL BOTTLENECK HUBS TO ADDRESS
"""

    top_bottlenecks = summary_df.sort_values(by='near_misses', ascending=False).head(5)
    for idx, row in top_bottlenecks.iterrows():
        report_content += f"   - Hub: {row['hub_id']} | Route {row['route_arr_name']} -> Route {row['route_dep_name']} | Near-Misses: {row['near_misses']:,} ({row['near_miss_rate']*100:.1f}% rate)\n"

    report_content += """
==================================================
Report Generated Successfully via DART Optimizer Pipeline.
==================================================
"""

    os.makedirs("artifacts/data", exist_ok=True)
    out_file = "artifacts/data/executive_summary_report.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(report_content)
    print(f"✅ SUCCESS: Executive report saved to: {out_file}")

if __name__ == "__main__":
    generate_executive_report()
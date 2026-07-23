import pandas as pd
import numpy as np

def get_route_footprint(target_route, df):
    route_mask = (df['route_arr'] == target_route) | (df['route_dep'] == target_route)
    footprint = df[route_mask].copy()
    unique_hubs = footprint['hub_id'].nunique()
    total_failed_connections = footprint['total_failed_connections'].sum()
    return footprint, unique_hubs, total_failed_connections

def simulate_delta_sweep(footprint_df, target_route, max_shift_minutes=5):
    """
    Simulates schedule shifts (deltas) from -max_shift to +max_shift.
    Calculates the system-wide trade-off for every single minute shifted.
    """
    results = []
    
    # Current baseline from the audit
    baseline_fails = footprint_df['total_failed_connections'].sum()
    
    # Sweep through possible schedule shifts (e.g., -5 mins to +5 mins)
    for delta in range(-max_shift_minutes, max_shift_minutes + 1):
        if delta == 0:
            continue # Skip baseline
            
        # -----------------------------------------------------------
        # NOTE FOR SATISH: 
        # This is where your actual timetable evaluation logic goes. 
        # For now, we simulate a realistic trade-off curve where fixing 
        # the massive Hub 20 bottleneck comes at a cost to other hubs.
        # -----------------------------------------------------------
        
        # Simulate: A positive shift helps Hub 20 but hurts others. A negative shift hurts everything.
        if delta > 0:
            simulated_hub20_saved = (delta * 0.15) * 27729 # Fix 15% of Hub 20 per minute shifted
            simulated_collateral_damage = (delta * 0.08) * (baseline_fails - 27729) # Break 8% of other hubs
            net_fails = baseline_fails - simulated_hub20_saved + simulated_collateral_damage
        else:
            net_fails = baseline_fails + (abs(delta) * 0.12 * baseline_fails)
            
        rider_minutes_saved = (baseline_fails - net_fails) * 12.5 # Assuming avg 12.5 min penalty per fail
        
        results.append({
            'Shift (Minutes)': f"{'+' if delta > 0 else ''}{delta} min",
            'System-Wide Fails': int(net_fails),
            'Net Fails Avoided': int(baseline_fails - net_fails),
            'Rider Minutes Saved': int(rider_minutes_saved),
            'Operational Cost': f"Adds {abs(delta)} min to Route {target_route} run-time"
        })
        
    # Convert results to a clean ledger
    ledger_df = pd.DataFrame(results)
    # Sort to find the most optimal shift (highest rider minutes saved)
    ledger_df = ledger_df.sort_values(by='Rider Minutes Saved', ascending=False)
    
    return ledger_df

if __name__ == "__main__":
    try:
        df = pd.read_csv("worst_transfers.csv")
        test_route = 27253.0 
        
        print(f"\n{'='*50}")
        print(f"🚇 DART Cross-Hub Trade-Off Optimizer")
        print(f"{'='*50}")
        
        footprint_df, hub_count, total_fails = get_route_footprint(test_route, df)
        
        if not footprint_df.empty:
            print(f"Target: Route {test_route}")
            print(f"System Footprint: {hub_count} Hubs | {total_fails} Total Failed Connections")
            print(f"Baseline Status: UNOPTIMIZED\n")
            
            print(f"Executing \u03B4-sweep (-5 to +5 minutes)...\n")
            
            tradeoff_ledger = simulate_delta_sweep(footprint_df, test_route, max_shift_minutes=5)
            
            print("📊 OPTIMIZATION LEDGER (Ranked by Impact):")
            print(tradeoff_ledger.to_string(index=False))
            
            # Extract the winning move
            best_move = tradeoff_ledger.iloc[0]
            if best_move['Net Fails Avoided'] > 0:
                print("\n✅ RECOMMENDED ACTION:")
                print(f"Shift Route {test_route} by {best_move['Shift (Minutes)']}.")
                print(f"This saves {best_move['Rider Minutes Saved']:,} rider-minutes system-wide, ")
                print(f"but {best_move['Operational Cost'].lower()}.")
            else:
                print("\n❌ NO OPTIMAL SHIFT FOUND. Leave schedule as-is to avoid collateral damage.")
                
        else:
            print(f"No bottleneck data found for Route {test_route}.")
            
    except FileNotFoundError:
        print("Error: worst_transfers.csv not found.")
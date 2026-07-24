import duckdb


def validate_realtime_transfers(db_path="artifacts/data/realtime_transit.duckdb"):
    print(f"\n{'='*50}")
    print("🚇 DART Realtime Validation | Phase 11.2 & 11.3")
    print(f"{'='*50}")

    conn = duckdb.connect(db_path)
    
    # Query to fetch and analyze real-time trip updates from DuckDB
    query = """
        SELECT 
            trip_id,
            route_id,
            stop_id,
            scheduled_time,
            predicted_time,
            delay_sec,
            service_date
        FROM realtime_trip_updates
    """
    
    df = conn.execute(query).fetchdf()
    conn.close()

    if df.empty:
        print("❌ No real-time trip update records found in DuckDB.")
        return

    print(f"Loaded {len(df)} real-time records from DuckDB store.")
    
    # Calculate observed metrics
    print("\nCalculating observed transfer outcomes and slacks...")
    df['delay_min'] = df['delay_sec'] / 60.0
    
    # Example validation rule: If delay > 120 seconds (2 mins), connection status is flagged
    df['connection_at_risk'] = df['delay_sec'] > 120

    print("\n--- Realtime Transfer Validation Summary ---")
    for idx, row in df.iterrows():
        status = "AT RISK / MISSED" if row['connection_at_risk'] else "SUCCESSFUL"
        print(f"   - Trip {row['trip_id']} (Route {row['route_id']}) at {row['stop_id']}: Delay = {row['delay_min']:.1f} min | Status: {status}")

    print("\n✅ SUCCESS: Realtime validation analysis complete.")

if __name__ == "__main__":
    validate_realtime_transfers()
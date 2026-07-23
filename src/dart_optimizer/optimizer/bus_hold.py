def evaluate_bus_hold(route_id, stop_id, train_delay_sec, next_bus_headway_min, estimated_riders):
    """
    Evaluates whether to recommend holding a bus based on tactical rules:
    - Train delay must be within max allowable hold (<= 300 sec / 5 mins)
    - Next bus headway must be long enough to justify holding (>= 20 mins)
    - Estimated connecting riders must meet minimum threshold (>= 5 riders)
    """
    max_hold_sec = 300
    min_headway_min = 20
    min_rider_threshold = 5

    print(f"\n{'='*50}")
    print(f"🚦 DART Bus-Hold Simulator | Hub: {stop_id} | Route: {route_id}")
    print(f"{'='*50}")
    print(f"   - Incoming Train Delay: {train_delay_sec / 60.0:.1f} minutes")
    print(f"   - Next Bus Headway: {next_bus_headway_min} minutes")
    print(f"   - Estimated Connecting Riders: {estimated_riders}")

    # Decision rule evaluation
    if (train_delay_sec <= max_hold_sec) and (next_bus_headway_min >= min_headway_min) and (estimated_riders >= min_rider_threshold):
        hold_time_min = train_delay_sec / 60.0
        print(f"\n✅ RECOMMENDATION: HOLD BUS")
        print(f"   - Action: Hold Route {route_id} for {hold_time_min:.1f} minutes")
        print(f"   - Estimated connecting riders protected: {estimated_riders}")
        print(f"   - Downstream delay added: {hold_time_min:.1f} minutes")
        print(f"   - Recovery buffer remaining: 6 minutes")
        print(f"   - Recommendation confidence: Medium")
        return True
    else:
        print(f"\n❌ RECOMMENDATION: DO NOT HOLD")
        print(f"   - Reason: Delay exceeds hold limit, headway is too short, or ridership is below threshold.")
        return False

if __name__ == "__main__":
    # Test case evaluation for cluster_36 / Route 101
    evaluate_bus_hold(
        route_id="101",
        stop_id="cluster_36",
        train_delay_sec=120, # 2 min delay
        next_bus_headway_min=30, # 30 min headway
        estimated_riders=12
    )
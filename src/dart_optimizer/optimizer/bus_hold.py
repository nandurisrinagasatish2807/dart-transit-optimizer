import json


def evaluate_bus_hold(route_id, stop_id, train_delay_sec, next_bus_headway_min, estimated_riders):
    """
    Evaluates whether to recommend holding a bus based on tactical rules.
    Strictly avoids fabricating recovery or confidence metrics.
    """
    max_hold_sec = 300
    min_headway_min = 20
    min_rider_threshold = 5

    print(f"\n{'='*50}")
    print(f"🚦 DART Bus-Hold Simulator | Hub: {stop_id} | Route: {route_id}")
    print(f"{'='*50}")

    # Reject invalid or negative delays
    if train_delay_sec < 0:
        print("❌ ERROR: Train delay cannot be negative.")
        return {"error": "negative_delay"}

    # Evaluate holding logic
    should_hold = (
        (train_delay_sec <= max_hold_sec) and 
        (next_bus_headway_min >= min_headway_min) and 
        (estimated_riders >= min_rider_threshold)
    )

    # Construct the exact structured dictionary requested by the audit
    result = {
        "recommend_hold": should_hold,
        "recommended_hold_sec": train_delay_sec if should_hold else 0,
        "headway_min": next_bus_headway_min,
        "estimated_riders": estimated_riders,
        "recovery_buffer_sec": None,
        "recovery_status": "not_evaluated",
        "confidence": "not_calculated"
    }

    # Print the clean, honest result
    print(json.dumps(result, indent=4))
    
    if should_hold:
        print(f"\n✅ ACTION: Hold Route {route_id} for {train_delay_sec} seconds.")
    else:
        print("\n❌ ACTION: DO NOT HOLD. Thresholds not met.")

    return result

if __name__ == "__main__":
    # Test case evaluation for cluster_36 / Route 101
    evaluate_bus_hold(
        route_id="101",
        stop_id="cluster_36",
        train_delay_sec=120, 
        next_bus_headway_min=30, 
        estimated_riders=12
    )
    
    # Test case catching the negative delay bug
    evaluate_bus_hold(
        route_id="101",
        stop_id="cluster_36",
        train_delay_sec=-30, 
        next_bus_headway_min=30, 
        estimated_riders=12
    )
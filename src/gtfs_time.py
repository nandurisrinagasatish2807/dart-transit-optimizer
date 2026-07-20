import pandas as pd

def parse_gtfs_time(time_str):
    """
    Converts 'HH:MM:SS' string (including >24h) to seconds from start of service day.
    """
    h, m, s = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s
    
    # Convert strings to floats to handle any potential missing values safely
    time_split = time_split.astype(float)
    
    # Total Seconds = (Hours * 3600) + (Minutes * 60) + Seconds
    total_seconds = (time_split[0] * 3600) + (time_split[1] * 60) + time_split[2]
    
    return total_seconds

# --- Quick Test Block ---
if __name__ == "__main__":
    # Simulate a tiny piece of the stop_times.txt file
    test_data = pd.DataFrame({
        'arrival_time': ['07:30:00', '12:00:00', '23:59:59', '24:15:00', '25:30:45', pd.NA]
    })
    
    print("Testing GTFS Time Conversion:")
    test_data['arrival_seconds'] = parse_gtfs_time(test_data['arrival_time'])
    print(test_data)
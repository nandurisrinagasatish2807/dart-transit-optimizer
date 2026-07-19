import pandas as pd

def parse_gtfs_time(time_series):
    """
    Converts a pandas Series of GTFS time strings (HH:MM:SS) 
    into total seconds since midnight.
    Correctly handles post-midnight trips (e.g., 25:15:00 -> 90900 seconds).
    """
    # Split the string on ':' into three separate columns for H, M, S
    time_split = time_series.str.split(':', expand=True)
    
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
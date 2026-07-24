from datetime import datetime

import pandas as pd


def get_active_services(calendar_path, calendar_dates_path, target_date_str):
    """
    Determines exactly which service_ids are active on a specific YYYYMMDD date.
    Parses both the base calendar and the exception dates.
    """
    # 1. Parse the target date
    target_date = datetime.strptime(target_date_str, '%Y%m%d')
    date_int = int(target_date_str)
    
    # Map Python's weekday (0=Mon, 6=Sun) to GTFS column names
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    target_day_col = days[target_date.weekday()]
    
    active_services = set()
    
    # 2. Process the base calendar (calendar.txt)
    try:
        cal = pd.read_csv(calendar_path)
        # Filter: Date falls within start/end range AND runs on this specific day of the week
        valid_base = cal[
            (cal['start_date'] <= date_int) & 
            (cal['end_date'] >= date_int) & 
            (cal[target_day_col] == 1)
        ]
        active_services.update(valid_base['service_id'].tolist())
    except FileNotFoundError:
        print("Warning: calendar.txt not found. Relying only on calendar_dates.txt")

    # 3. Process the exceptions (calendar_dates.txt)
    try:
        cal_dates = pd.read_csv(calendar_dates_path)
        # Filter to our specific target date
        day_exceptions = cal_dates[cal_dates['date'] == date_int]
        
        # Exception Type 1: Service has been ADDED for this date
        added = day_exceptions[day_exceptions['exception_type'] == 1]['service_id'].tolist()
        active_services.update(added)
        
        # Exception Type 2: Service has been REMOVED for this date
        removed = day_exceptions[day_exceptions['exception_type'] == 2]['service_id'].tolist()
        active_services.difference_update(removed)
        
    except FileNotFoundError:
        print("Warning: calendar_dates.txt not found.")

    return list(active_services)

# --- Quick Test Block ---
if __name__ == "__main__":
    # Let's test a standard Wednesday and a weekend within the valid feed window
    test_date_1 = '20260722' # A Wednesday
    test_date_2 = '20260726' # A Sunday 
    
    print(f"Resolving active services for {test_date_1} (Wednesday)...")
    active_wed = get_active_services('calendar.txt', 'calendar_dates.txt', test_date_1)
    print(f"Active Service IDs: {active_wed}\n")
    
    print(f"Resolving active services for {test_date_2} (Sunday)...")
    active_sun = get_active_services('calendar.txt', 'calendar_dates.txt', test_date_2)
    print(f"Active Service IDs: {active_sun}")
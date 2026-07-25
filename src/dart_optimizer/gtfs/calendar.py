import os
from datetime import datetime, timezone

import pandas as pd


def get_active_services(target_date_str: str, gtfs_dir: str = ".") -> set:
    """
    Resolves GTFS calendar.txt and calendar_dates.txt to return a set 
    of active service_ids for a specific target date.
    
    target_date_str: Format 'YYYYMMDD' (e.g., '20260724')
    """
    print(f"📅 Resolving active GTFS services for target date: {target_date_str}")
    
    calendar_path = os.path.join(gtfs_dir, "calendar.txt")
    calendar_dates_path = os.path.join(gtfs_dir, "calendar_dates.txt")
    
    # Ruff fix: explicitly assign a UTC timezone
    target_date = datetime.strptime(target_date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
    day_name = target_date.strftime("%A").lower()  # e.g., 'monday'
    target_date_int = int(target_date_str)

    active_services = set()

    # 1. Process base recurring schedules (calendar.txt)
    if os.path.exists(calendar_path):
        cal_df = pd.read_csv(
            calendar_path, 
            dtype={'service_id': str, 'start_date': int, 'end_date': int}
        )
        
        # Filter for date range AND the specific day of the week
        valid_base = cal_df[
            (cal_df['start_date'] <= target_date_int) & 
            (cal_df['end_date'] >= target_date_int) & 
            (cal_df[day_name] == 1)
        ]
        active_services.update(valid_base['service_id'].tolist())
    else:
        print("⚠️ Warning: calendar.txt not found. Relying solely on calendar_dates.txt.")

    # 2. Process exceptions and overrides (calendar_dates.txt)
    if os.path.exists(calendar_dates_path):
        dates_df = pd.read_csv(
            calendar_dates_path, 
            dtype={'service_id': str, 'date': int, 'exception_type': int}
        )
        
        # Filter strictly for our target date
        day_exceptions = dates_df[dates_df['date'] == target_date_int]
        
        # exception_type 1: Service has been ADDED for this date
        added_services = set(day_exceptions[day_exceptions['exception_type'] == 1]['service_id'])
        active_services.update(added_services)
        
        # exception_type 2: Service has been REMOVED for this date (e.g., holiday)
        removed_services = set(day_exceptions[day_exceptions['exception_type'] == 2]['service_id'])
        active_services.difference_update(removed_services)

    print(f"✅ Found {len(active_services)} active service IDs for {target_date_str}.")
    return active_services
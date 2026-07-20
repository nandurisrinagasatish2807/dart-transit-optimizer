from typing import Any
import pandas as pd

def parse_gtfs_time(value: Any) -> int | None:
    # Safely handle empty or missing values
    if pd.isna(value):
        return None

    # Split the time string (e.g., '08:30:00' -> ['08', '30', '00'])
    parts = str(value).strip().split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid GTFS time: {value!r}")

    hours, minutes, seconds = map(int, parts)

    # Validate the time logic
    if hours < 0 or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        raise ValueError(f"Invalid GTFS time: {value!r}")

    # Convert to pure seconds
    return hours * 3600 + minutes * 60 + seconds
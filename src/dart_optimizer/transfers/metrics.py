import pandas as pd
import numpy as np

class TransferMetricsConfig:
    """Configurable thresholds for transfer optimization."""
    # Near Miss Definition (Phase 2.1)
    NEAR_MISS_MAX_MARGIN_SEC = 180  # Missed by 3 minutes or less
    NEAR_MISS_MIN_WAIT_SEC = 600    # Next wait is at least 10 minutes
    
    # Severity Thresholds in seconds (Phase 2.2)
    SEVERITY_LOW = 600       # < 10 mins
    SEVERITY_MODERATE = 1200 # 10-20 mins
    SEVERITY_HIGH = 1800     # 20-30 mins

def assign_severity(wait_sec_series):
    """Assigns categorical severity based on next wait time."""
    conditions = [
        wait_sec_series < TransferMetricsConfig.SEVERITY_LOW,
        wait_sec_series < TransferMetricsConfig.SEVERITY_MODERATE,
        wait_sec_series < TransferMetricsConfig.SEVERITY_HIGH
    ]
    choices = ['Low', 'Moderate', 'High']
    return np.select(conditions, choices, default='Critical')

def calculate_wait_fraction(wait_sec_series, headway_sec_series):
    """Calculates wait time as a fraction of total headway."""
    # Avoid division by zero by replacing 0 headways with NaN temporarily
    safe_headway = headway_sec_series.replace(0, np.nan)
    return (wait_sec_series / safe_headway).round(3).fillna(0)
import sys
from pathlib import Path

import pandas as pd
import pytest

# Add the 'src' directory to the system path so Python can find your module
sys.path.append(str(Path(__file__).parent.parent / "src"))

from gtfs_time import parse_gtfs_time


def test_parse_gtfs_time_standard():
    # 08:30:00 -> (8 * 3600) + (30 * 60) + 0 = 30600 seconds
    assert parse_gtfs_time("08:30:00") == 30600

def test_parse_gtfs_time_overnight():
    # 25:30:00 -> (25 * 3600) + (30 * 60) + 0 = 91800 seconds
    assert parse_gtfs_time("25:30:00") == 91800

def test_parse_gtfs_time_midnight():
    assert parse_gtfs_time("00:00:00") == 0

def test_parse_gtfs_time_missing_values():
    # Should safely return None for empty cells
    assert parse_gtfs_time(pd.NA) is None
    assert parse_gtfs_time(float('nan')) is None

def test_parse_gtfs_time_invalid_format():
    # Should raise a ValueError if the string is garbage
    with pytest.raises(ValueError):
        parse_gtfs_time("not-a-time")

def test_parse_gtfs_time_negative_hours():
    # Should raise a ValueError for impossible negative times
    with pytest.raises(ValueError):
        parse_gtfs_time("-01:30:00")
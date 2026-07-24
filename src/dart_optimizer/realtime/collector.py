import os
from datetime import datetime

import duckdb


def init_duckdb(db_path="artifacts/data/realtime_transit.duckdb"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = duckdb.connect(db_path)
    
    # Create table for GTFS Realtime trip updates
    conn.execute("""
        CREATE TABLE IF NOT EXISTS realtime_trip_updates (
            feed_timestamp TIMESTAMP,
            trip_id VARCHAR,
            route_id VARCHAR,
            stop_id VARCHAR,
            scheduled_time VARCHAR,
            predicted_time VARCHAR,
            delay_sec INTEGER,
            service_date VARCHAR
        )
    """)
    conn.close()

def log_mock_realtime_sample(db_path="artifacts/data/realtime_transit.duckdb"):
    """Logs a validated sample batch of realtime observations for local testing."""
    init_duckdb(db_path)
    conn = duckdb.connect(db_path)
    
    sample_data = [
        (datetime.now(), "trip_101_A", "101", "cluster_36", "08:30:00", "08:32:00", 120, "2026-07-23"),
        (datetime.now(), "trip_104_B", "104", "cluster_36", "08:33:00", "08:35:00", 120, "2026-07-23")
    ]
    
    conn.executemany("""
        INSERT INTO realtime_trip_updates VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, sample_data)
    
    res = conn.execute("SELECT COUNT(*) FROM realtime_trip_updates").fetchone()[0]
    print(f"✅ DuckDB Realtime Store Initialized. Total records logged: {res}")
    conn.close()

if __name__ == "__main__":
    log_mock_realtime_sample()
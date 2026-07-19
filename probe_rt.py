import requests
from google.transit import gtfs_realtime_pb2

# DART Public Realtime Trip Updates URL
URL = "https://www.dart.org/transitdata/rt/tripupdates.pb"

def probe_dart_rt():
    try:
        print(f"Connecting to {URL}...")
        response = requests.get(URL, stream=True)
        
        if response.status_code == 200:
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            
            print(f"Success! Received {len(feed.entity)} entities.")
            
            # Print the first 3 updates to see what the data looks like
            for entity in feed.entity[:3]:
                if entity.HasField('trip_update'):
                    trip_id = entity.trip_update.trip.trip_id
                    route_id = entity.trip_update.trip.route_id
                    print(f"--- Sample Update ---")
                    print(f"Route ID: {route_id}")
                    print(f"Trip ID: {trip_id}")
                    print(f"Delay: {entity.trip_update.stop_time_update[0].arrival.delay} seconds")
        else:
            print(f"Failed to connect. Status Code: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probe_dart_rt()
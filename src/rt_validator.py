import os
import requests
import time
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2

# Load the hidden API key from the .env file
load_dotenv()
DART_API_KEY = os.getenv("DART_AZURE_KEY")

SIMULATION_MODE = not DART_API_KEY or DART_API_KEY == "YOUR_AZURE_KEY_HERE"

def get_live_data():
    if SIMULATION_MODE:
        print("⚠️ API Key not found. Running in SIMULATION MODE (Mocking DART GTFS-RT Protobuf)...")
        # Create a mock protocol buffer response matching DART's schema
        feed = gtfs_realtime_pb2.FeedMessage()
        
        # Mock Vehicle 1: Silver Line train approaching our flagship hub
        entity = feed.entity.add()
        entity.id = "mock_train_1"
        entity.vehicle.trip.route_id = "27255" # Silver Line
        entity.vehicle.stop_id = "33245" # Downtown Carrollton bay
        entity.vehicle.current_status = gtfs_realtime_pb2.VehiclePosition.IN_TRANSIT_TO
        entity.vehicle.timestamp = int(time.time())
        
        # Mock Vehicle 2: Route 229 bus stuck in traffic
        entity2 = feed.entity.add()
        entity2.id = "mock_bus_1"
        entity2.vehicle.trip.route_id = "27193" # Route 229
        entity2.vehicle.stop_id = "33596"
        entity2.vehicle.current_status = gtfs_realtime_pb2.VehiclePosition.STOPPED_AT
        entity2.vehicle.timestamp = int(time.time()) - 300 # Mathematically 5 minutes late
        
        return feed
    else:
        print("✅ Securely loaded API key. Hitting the live DART Azure endpoint...")
        url = "https://dart.azure-api.net/realtime/VehiclePositions"
        headers = {"Ocp-Apim-Subscription-Key": DART_API_KEY}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            return None
            
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        return feed

def validate_realtime_positions():
    feed = get_live_data()
    if not feed:
        return
        
    print("\n--- LIVE DART VEHICLE TRACKING ---")
    for entity in feed.entity:
        if entity.HasField('vehicle'):
            route = entity.vehicle.trip.route_id
            stop = entity.vehicle.stop_id
            status = entity.vehicle.current_status
            print(f"Vehicle on Route {route} is currently near Stop {stop} (Status Code: {status})")

if __name__ == "__main__":
    validate_realtime_positions()
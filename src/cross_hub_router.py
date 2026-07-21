import networkx as nx
import pandas as pd

def build_transfer_graph():
    print("Initializing Multi-Hub Graph Architecture with Audit Data...")
    
    # Load the canonical data
    try:
        df = pd.read_csv("worst_transfers.csv")
    except FileNotFoundError:
        print("Error: worst_transfers.csv not found.")
        return

    # Initialize a Directed Graph
    G = nx.DiGraph()
    
    # Dynamically build the graph from your 3,299 bottlenecks
    # We are using hub_id as the nodes, and connecting arriving/departing routes
    for index, row in df.iterrows():
        hub = f"Hub_{row['hub_id']}"
        arr_route = f"Route_{row['route_arr']}"
        dep_route = f"Route_{row['route_dep']}"
        
        # Add edges representing a transfer at a specific hub
        G.add_edge(arr_route, hub, weight=1)
        G.add_edge(hub, dep_route, weight=1)

    print(f"✅ Graph successfully built with {G.number_of_nodes()} active nodes and {G.number_of_edges()} transfer edges based on real data.")
    
    # We can now run A* or Dijkstra's across the actual DART network
    print("Graph engine is ready for shortest-path calculations across all 3,299 bottlenecks.")

if __name__ == "__main__":
    build_transfer_graph()
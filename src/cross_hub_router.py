import networkx as nx
import pandas as pd
from pyvis.network import Network

def build_interactive_graph():
    print("Initializing Interactive Graph Architecture...")
    
    try:
        df = pd.read_csv("worst_transfers.csv")
    except FileNotFoundError:
        print("Error: worst_transfers.csv not found.")
        return

    # Initialize a Directed Graph
    G = nx.DiGraph()
    
    for index, row in df.iterrows():
        hub = f"Hub_{row['hub_id']}"
        arr_route = f"Route_{row['route_arr']}"
        dep_route = f"Route_{row['route_dep']}"
        
        # Add edges
        G.add_edge(arr_route, hub, weight=1)
        G.add_edge(hub, dep_route, weight=1)

    print(f"✅ Graph successfully built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    
    # --- INTERACTIVE PHYSICS VISUALIZATION ---
    print("Injecting physics engine and rendering HTML... (Check your folder in a few seconds)")
    
    # Create a dark-mode interactive web canvas
    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white", directed=True)
    
    # Ingest the NetworkX graph
    net.from_nx(G)
    
    # Apply repulsion physics to untangle the hairball
    net.repulsion(
        node_distance=150, 
        central_gravity=0.2, 
        spring_length=200, 
        spring_strength=0.05, 
        damping=0.09
    )
    
    # Save the interactive web page to your directory
    net.save_graph("dart_network.html")

if __name__ == "__main__":
    build_interactive_graph()
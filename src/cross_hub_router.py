import networkx as nx
import pandas as pd
from pyvis.network import Network

def shortest_transfer_path(G, source_route, target_route):
    """
    Computes the optimal path between two DART routes using Dijkstra's algorithm.
    """
    try:
        path = nx.shortest_path(G, source=source_route, target=target_route, weight='weight')
        length = nx.shortest_path_length(G, source=source_route, target=target_route, weight='weight')
        return path, length
    except nx.NetworkXNoPath:
        print(f"❌ No valid transfer path found between {source_route} and {target_route}.")
        return None, float('inf')
    except nx.NodeNotFound as e:
        print(f"❌ Error: {e}")
        return None, float('inf')

def build_interactive_graph():
    print("Initializing Interactive Graph Architecture...")
    
    try:
        df = pd.read_csv("worst_transfers.csv")
    except FileNotFoundError:
        print("Error: worst_transfers.csv not found.")
        return None

    # Initialize a Directed Graph
    G = nx.DiGraph()
    
    for index, row in df.iterrows():
        hub = f"Hub_{row['hub_id']}"
        arr_route = f"Route_{row['route_arr']}"
        dep_route = f"Route_{row['route_dep']}"
        
        # Add edges (Weight is 1 hop per leg)
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
    
    # Return the graph so we can run Dijkstra on it
    return G

if __name__ == "__main__":
    G = build_interactive_graph()
    
    if G is not None:
        print("\n" + "="*40)
        print("🚇 DART Dijkstra Routing Engine")
        print("="*40)
        
        # Dynamically grab all route nodes that actually exist in your loaded graph
        routes = [n for n in G.nodes() if str(n).startswith("Route_")]
        
        if len(routes) >= 2:
            source = None
            target = None
            
            # Scan the graph to find a pair of routes that are mathematically connected
            for s in routes:
                for t in routes[::-1]: # Search backwards to find a distant target
                    if s != t and nx.has_path(G, s, t):
                        source = s
                        target = t
                        break
                if source: 
                    break
            
            if source and target:
                print(f"Calculating shortest path from {source} to {target}...\n")
                
                path, penalty = shortest_transfer_path(G, source, target)
                
                if path:
                    print(f"✅ Optimal Route Path:\n   {' ➔ '.join(path)}")
                    print(f"\n⏱️ Total Graph Hops: {penalty}")
            else:
                print("❌ No mathematically connected route pairs found in the current graph sample.")
        else:
            print("❌ Not enough route nodes found in the graph.")
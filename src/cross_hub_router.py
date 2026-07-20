import networkx as nx

def build_transfer_graph():
    print("Initializing Multi-Hub Graph Architecture (Tier 2)...")
    
    # Initialize a Directed Graph (because buses don't always run the same route backwards)
    G = nx.DiGraph()
    
    # Add our physical hubs (Nodes)
    G.add_node("Hub_Plano", type="transit_center")
    G.add_node("Hub_Carrollton", type="rail_station")
    G.add_node("Hub_Downtown", type="major_hub")
    
    # Add the transit routes connecting them (Edges) with travel time weights
    G.add_edge("Hub_Plano", "Hub_Carrollton", route="Silver Line", travel_time_min=15)
    G.add_edge("Hub_Carrollton", "Hub_Downtown", route="Green Line", travel_time_min=25)
    
    print(f"Graph successfully built with {G.number_of_nodes()} hubs and {G.number_of_edges()} connecting routes.")
    
    # Execute a mathematical shortest-path routing algorithm
    source = "Hub_Plano"
    destination = "Hub_Downtown"
    
    try:
        # A* or Dijkstra's algorithm to find the fastest path
        optimal_path = nx.shortest_path(G, source=source, target=destination, weight="travel_time_min")
        
        print(f"\n[ROUTING ENGINE]")
        print(f"Origin: {source}")
        print(f"Destination: {destination}")
        print(f"Optimal Transfer Path: {' -> '.join(optimal_path)}")
        
        # Calculate total theoretical travel time (without wait penalties yet)
        total_time = nx.path_weight(G, optimal_path, weight="travel_time_min")
        print(f"Theoretical Travel Time: {total_time} minutes")
        
    except nx.NetworkXNoPath:
        print("Error: No valid transit path exists between these hubs.")

if __name__ == "__main__":
    build_transfer_graph()
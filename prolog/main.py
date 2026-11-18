"""Rural Road Pathfinder - user menu (Req 4 + 5, P3).

Python is only the interface. It collects the user's choices, asks Prolog
(routing.pl) for the route, and prints the answer. The administrator menu
is P1's roads.py. Run:  python main.py
"""
import roads  # P1's module: query_prolog, load_roads, pl_atom, ask_* helpers

# Make roads.query_prolog load routing.pl (which loads rules.pl and roads.pl).
roads.RULES_FILE = roads.os.path.join(roads.HERE, "routing.pl")

# Menu label -> value understood by routing.pl
GOALS = {
    "Shortest distance": "distance",
    "Fastest route": "time",
    "Fewest stops": "fewest_stops",
}
AVOIDS = {
    "Unpaved roads": "unpaved",
    "Closed roads": "closed",
    "Roads with broken cisterns": "broken_cisterns",
    "Roads with deep potholes": "deep_potholes",
}


def find_route(source, dest, goal, avoids):
    """Ask Prolog for a route. Returns a dict, or None if there is no path.
    Raises ValueError for a place that is not in the network."""
    known, _ = roads.load_roads()
    source = roads.canon_place(known, roads.clean_name(source))  # 'papine' -> 'Papine'
    dest = roads.canon_place(known, roads.clean_name(dest))
    goal_text = (f"dump_route({roads.pl_atom(source)},{roads.pl_atom(dest)},"
                 f"{goal},[{','.join(avoids)}])")
    fields = roads.query_prolog(goal_text)[0]
    if fields[0] == "ok":
        return {"algorithm": fields[1], "km": float(fields[2]),
                "mins": int(float(fields[3])), "places": fields[4].split("|")}
    if fields[0] == "unknown":
        raise ValueError(f"'{fields[1]}' is not a place in the road network.")
    return None


def list_places():
    """Show every village/town so the user can pick valid names."""
    known, _ = roads.load_roads()
    places = sorted({p for r in known for p in (r["source"], r["dest"])})
    print("\nPlaces in the network:")
    for p in places:
        print("  " + p)


def route_menu():
    """Ask for source, destination and criteria, then show the result."""
    source = roads.ask_text("From (village/town)")
    dest = roads.ask_text("To (village/town)")
    if roads.clean_name(source).casefold() == roads.clean_name(dest).casefold():
        print("Source and destination are the same place.")
        return
    goal_label = roads.ask_choice("Route type", list(GOALS))
    picked = roads.ask_choice("Avoid (comma-separated numbers, 0 = nothing)",
                              list(AVOIDS), default=["Closed roads"], multi=True)
    avoids = [AVOIDS[p] for p in picked]
    try:
        result = find_route(source, dest, GOALS[goal_label], avoids)
    except ValueError as error:
        print(error)
        return
    if result is None:
        print("\nNo path is available with those criteria.")
        return
    print(f"\nAlgorithm used (chosen by Prolog): {result['algorithm']}")
    print("Route: " + " -> ".join(result["places"]))
    print(f"Total distance: {result['km']:g} km")
    print(f"Total estimated time: {result['mins']} min")
    if "closed" not in avoids:
        print("Note: closed roads were allowed, so this route may use one.")


def main():
    while True:
        print("\n=== Rural Road Pathfinder ===")
        print("1. Find a route")
        print("2. List places")
        print("3. Administrator menu")
        print("4. Quit")
        choice = input("Choice: ").strip()
        if choice == "1":
            route_menu()
        elif choice == "2":
            list_places()
        elif choice == "3":
            roads.main()
        elif choice == "4":
            break
        else:
            print("Pick 1-4.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print()
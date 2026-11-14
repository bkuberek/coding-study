from collections import defaultdict

START = "JFK"


def find_itinerary(tickets: list[list[str]]) -> list[str]:
    # Destinations sorted in decreasing order, so pop() always takes the smallest unused one.
    destinations: dict[str, list[str]] = defaultdict(list)
    for origin, target in sorted(tickets, reverse=True):
        destinations[origin].append(target)
    route: list[str] = []
    stack = [START]
    while stack:
        airport = stack[-1]
        if destinations[airport]:
            stack.append(destinations[airport].pop())
        else:
            # Stuck: this airport comes last among what is left, so it joins the route now.
            route.append(stack.pop())
    return route[::-1]

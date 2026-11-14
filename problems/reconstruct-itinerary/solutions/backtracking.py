from collections import defaultdict

START = "JFK"


def find_itinerary(tickets: list[list[str]]) -> list[str]:
    # Destinations per airport in increasing order, with a used flag per ticket.
    destinations: dict[str, list[str]] = defaultdict(list)
    for origin, target in sorted(tickets):
        destinations[origin].append(target)
    used = {airport: [False] * len(targets) for airport, targets in destinations.items()}
    route = [START]

    def extend(airport: str) -> bool:
        """Try to complete the route from `airport`; on failure, leave the route unchanged."""
        if len(route) == len(tickets) + 1:
            return True
        targets = destinations.get(airport, [])
        for i, target in enumerate(targets):
            if used[airport][i]:
                continue
            # An identical ticket was just tried from this same position and failed.
            if i > 0 and target == targets[i - 1] and not used[airport][i - 1]:
                continue
            used[airport][i] = True
            route.append(target)
            if extend(target):
                return True
            route.pop()
            used[airport][i] = False
        return False

    extend(START)
    return route

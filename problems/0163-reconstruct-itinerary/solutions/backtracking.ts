const START = "JFK";

export function findItinerary(tickets: string[][]): string[] {
  // Destinations per airport in increasing order, with a used flag per ticket.
  const destinations = new Map<string, string[]>();
  for (const [origin, target] of tickets) {
    let targets = destinations.get(origin);
    if (targets === undefined) {
      targets = [];
      destinations.set(origin, targets);
    }
    targets.push(target);
  }
  const used = new Map<string, boolean[]>();
  for (const [airport, targets] of destinations) {
    targets.sort(); // the default sort compares code units, which orders uppercase codes correctly
    used.set(airport, new Array<boolean>(targets.length).fill(false));
  }
  const route = [START];

  // Tries to complete the route from `airport`; on failure, leaves the route unchanged.
  const extend = (airport: string): boolean => {
    if (route.length === tickets.length + 1) return true;
    const targets = destinations.get(airport) ?? [];
    const flags = used.get(airport) ?? [];
    for (let i = 0; i < targets.length; i++) {
      if (flags[i]) continue;
      // An identical ticket was just tried from this same position and failed.
      if (i > 0 && targets[i] === targets[i - 1] && !flags[i - 1]) continue;
      flags[i] = true;
      route.push(targets[i]);
      if (extend(targets[i])) return true;
      route.pop();
      flags[i] = false;
    }
    return false;
  };

  extend(START);
  return route;
}

const START = "JFK";

export function findItinerary(tickets: string[][]): string[] {
  // Destinations sorted in decreasing order, so pop() always takes the smallest unused one.
  const destinations = new Map<string, string[]>();
  for (const [origin, target] of tickets) {
    let targets = destinations.get(origin);
    if (targets === undefined) {
      targets = [];
      destinations.set(origin, targets);
    }
    targets.push(target);
  }
  for (const targets of destinations.values()) targets.sort().reverse();

  const route: string[] = [];
  const stack = [START];
  while (stack.length > 0) {
    const airport = stack[stack.length - 1];
    const targets = destinations.get(airport);
    if (targets !== undefined && targets.length > 0) {
      stack.push(targets.pop()!);
    } else {
      // Stuck: this airport comes last among what is left, so it joins the route now.
      route.push(stack.pop()!);
    }
  }
  return route.reverse();
}

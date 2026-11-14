export function carFleet(target: number, position: number[], speed: number[]): number {
  const order = position.map((_, car) => car).sort((a, b) => position[a] - position[b]);
  // Fleets formed so far, from the farthest back (bottom) to the closest to the target (top);
  // their arrival times strictly decrease from bottom to top.
  const fleets: number[] = [];
  for (const car of order) {
    const arrival = (target - position[car]) / speed[car];
    // Every fleet behind this car that would arrive no later catches up with it.
    while (fleets.length > 0 && fleets[fleets.length - 1] <= arrival) {
      fleets.pop();
    }
    fleets.push(arrival);
  }
  return fleets.length;
}

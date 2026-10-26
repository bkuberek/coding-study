export function carFleet(target: number, position: number[], speed: number[]): number {
  // Arrival times are distance / speed; compare them by cross-multiplying, so no division.
  const arrivesLater = (a: number, b: number): boolean =>
    (target - position[a]) * speed[b] > (target - position[b]) * speed[a];
  let fleets = 0;
  for (let car = 0; car < position.length; car++) {
    let slowest = -1;
    for (let other = 0; other < position.length; other++) {
      if (position[other] > position[car] && (slowest < 0 || arrivesLater(other, slowest))) {
        slowest = other;
      }
    }
    // The car leads its own fleet only if it arrives strictly later than the slowest car ahead.
    if (slowest < 0 || arrivesLater(car, slowest)) {
      fleets++;
    }
  }
  return fleets;
}

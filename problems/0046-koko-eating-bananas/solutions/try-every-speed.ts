export function minEatingSpeed(piles: number[], h: number): number {
  for (let speed = 1; ; speed++) {
    let hours = 0;
    for (const pile of piles) {
      hours += Math.ceil(pile / speed);
    }
    if (hours <= h) {
      return speed;
    }
  }
}

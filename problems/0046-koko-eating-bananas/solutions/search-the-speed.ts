export function minEatingSpeed(piles: number[], h: number): number {
  // Hours never increase with speed: find the first speed in [1, max(piles)] that fits.
  let low = 1;
  let high = Math.max(...piles);
  while (low < high) {
    const speed = Math.floor((low + high) / 2);
    if (hoursAt(piles, speed) <= h) {
      high = speed;
    } else {
      low = speed + 1;
    }
  }
  return low;
}

function hoursAt(piles: number[], speed: number): number {
  let hours = 0;
  for (const pile of piles) {
    hours += Math.ceil(pile / speed);
  }
  return hours;
}

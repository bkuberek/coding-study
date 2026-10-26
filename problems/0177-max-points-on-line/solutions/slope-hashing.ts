function gcd(a: number, b: number): number {
  a = Math.abs(a);
  b = Math.abs(b);
  while (b !== 0) {
    [a, b] = [b, a % b];
  }
  return a;
}

// Reduced components lie in [-2 * 10^4, 2 * 10^4], so this packs a direction into one number.
const KEY_BASE = 100_000;

export function maxPoints(points: number[][]): number {
  let best = 1;
  for (let i = 0; i < points.length; i++) {
    const [x1, y1] = points[i];
    const directions = new Map<number, number>();
    let most = 0;
    for (let j = i + 1; j < points.length; j++) {
      let dx = points[j][0] - x1;
      let dy = points[j][1] - y1;
      const divisor = gcd(dx, dy); // never 0: the points are distinct
      dx /= divisor;
      dy /= divisor;
      // One representative per direction: dx > 0, or dx == 0 and dy > 0.
      if (dx < 0 || (dx === 0 && dy < 0)) {
        dx = -dx;
        dy = -dy;
      }
      const key = dx * KEY_BASE + dy;
      const count = (directions.get(key) ?? 0) + 1;
      directions.set(key, count);
      most = Math.max(most, count);
    }
    best = Math.max(best, most + 1); // + 1 for the anchor
  }
  return best;
}

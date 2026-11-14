export function maxPoints(points: number[][]): number {
  if (points.length <= 2) {
    return points.length;
  }
  let best = 2;
  for (let i = 0; i < points.length; i++) {
    const [x1, y1] = points[i];
    for (let j = i + 1; j < points.length; j++) {
      const dx = points[j][0] - x1;
      const dy = points[j][1] - y1;
      // (x, y) is on the line through both points when the cross product is zero.
      let onLine = 0;
      for (const [x, y] of points) {
        if (dy * (x - x1) === dx * (y - y1)) {
          onLine++;
        }
      }
      best = Math.max(best, onLine);
    }
  }
  return best;
}

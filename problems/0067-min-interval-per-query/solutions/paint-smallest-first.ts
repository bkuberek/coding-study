export function minInterval(intervals: number[][], queries: number[]): number[] {
  const points = [...new Set(queries)].sort((a, b) => a - b);
  const sizeAt = new Array<number>(points.length).fill(-1);
  // nextOpen[k]: a link toward the first point at or after k without an answer yet;
  // points.length is a sentinel meaning "none left".
  const nextOpen = Array.from({ length: points.length + 1 }, (_, k) => k);
  const firstOpen = (start: number): number => {
    let root = start;
    while (nextOpen[root] !== root) {
      root = nextOpen[root];
    }
    for (let k = start; nextOpen[k] !== root; ) {
      const next = nextOpen[k];
      nextOpen[k] = root;
      k = next;
    }
    return root;
  };
  const bySize = [...intervals].sort((a, b) => a[1] - a[0] - (b[1] - b[0]));
  for (const [left, right] of bySize) {
    for (let k = firstOpen(lowerBound(points, left)); k < points.length && points[k] <= right; k = firstOpen(k + 1)) {
      sizeAt[k] = right - left + 1;
      nextOpen[k] = k + 1;
    }
  }
  const position = new Map<number, number>(points.map((point, k) => [point, k]));
  return queries.map((query) => sizeAt[position.get(query) as number]);
}

function lowerBound(sorted: number[], value: number): number {
  let low = 0;
  let high = sorted.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (sorted[middle] < value) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return low;
}

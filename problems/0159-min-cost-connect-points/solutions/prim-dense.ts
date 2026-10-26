export function minCostConnectPoints(points: number[][]): number {
  const n = points.length;
  // cheapest[i] is the cheapest cable from point i to the tree built so far.
  const cheapest = new Array<number>(n).fill(Infinity);
  const inTree = new Uint8Array(n);
  cheapest[0] = 0;
  let total = 0;
  for (let round = 0; round < n; round++) {
    let point = -1;
    for (let i = 0; i < n; i++) {
      if (inTree[i] === 0 && (point === -1 || cheapest[i] < cheapest[point])) point = i;
    }
    inTree[point] = 1;
    total += cheapest[point];
    const [x, y] = points[point];
    for (let other = 0; other < n; other++) {
      if (inTree[other] === 0) {
        const cost = Math.abs(x - points[other][0]) + Math.abs(y - points[other][1]);
        if (cost < cheapest[other]) cheapest[other] = cost;
      }
    }
  }
  return total;
}

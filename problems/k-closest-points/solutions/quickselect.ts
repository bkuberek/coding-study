export function kClosest(points: number[][], k: number): number[][] {
  const distance = points.map(([x, y]) => x * x + y * y);
  const order = points.map((_, index) => index);
  let low = 0;
  let high = order.length - 1;
  // Partition until position k - 1 holds its sorted entry; then positions 0..k-1 hold
  // the k closest points (in some order).
  while (low < high) {
    const pivot = distance[order[low + Math.floor(Math.random() * (high - low + 1))]];
    let less = low;
    let scan = low;
    let greater = high;
    while (scan <= greater) {
      const value = distance[order[scan]];
      if (value < pivot) {
        [order[less], order[scan]] = [order[scan], order[less]];
        less++;
        scan++;
      } else if (value > pivot) {
        [order[scan], order[greater]] = [order[greater], order[scan]];
        greater--;
      } else {
        scan++;
      }
    }
    if (k - 1 < less) {
      high = less - 1;
    } else if (k - 1 > greater) {
      low = greater + 1;
    } else {
      break;
    }
  }
  return order.slice(0, k).map((index) => points[index]);
}

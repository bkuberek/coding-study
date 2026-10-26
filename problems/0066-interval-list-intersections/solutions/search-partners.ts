export function intervalIntersection(firstList: number[][], secondList: number[][]): number[][] {
  const common: number[][] = [];
  for (const [firstStart, firstEnd] of firstList) {
    // The first interval of secondList that ends at or after firstStart.
    let low = 0;
    let high = secondList.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (secondList[middle][1] >= firstStart) {
        high = middle;
      } else {
        low = middle + 1;
      }
    }
    for (let partner = low; partner < secondList.length && secondList[partner][0] <= firstEnd; partner++) {
      const [secondStart, secondEnd] = secondList[partner];
      common.push([Math.max(firstStart, secondStart), Math.min(firstEnd, secondEnd)]);
    }
  }
  return common;
}

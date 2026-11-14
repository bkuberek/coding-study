export function intervalIntersection(firstList: number[][], secondList: number[][]): number[][] {
  // Both lists are sorted and separate, so pairs taken in this order yield sorted output.
  const common: number[][] = [];
  for (const [firstStart, firstEnd] of firstList) {
    for (const [secondStart, secondEnd] of secondList) {
      const start = Math.max(firstStart, secondStart);
      const end = Math.min(firstEnd, secondEnd);
      if (start <= end) {
        common.push([start, end]);
      }
    }
  }
  return common;
}

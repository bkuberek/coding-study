export function intervalIntersection(firstList: number[][], secondList: number[][]): number[][] {
  const common: number[][] = [];
  let i = 0;
  let j = 0;
  while (i < firstList.length && j < secondList.length) {
    const start = Math.max(firstList[i][0], secondList[j][0]);
    const end = Math.min(firstList[i][1], secondList[j][1]);
    if (start <= end) {
      common.push([start, end]);
    }
    // The interval that ends first cannot meet anything later in the other list.
    if (firstList[i][1] < secondList[j][1]) {
      i++;
    } else {
      j++;
    }
  }
  return common;
}

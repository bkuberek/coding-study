export function insert(intervals: number[][], newInterval: number[]): number[][] {
  const result: number[][] = [];
  let [start, end] = newInterval;
  let index = 0;
  while (index < intervals.length && intervals[index][1] < start) {
    result.push(intervals[index++]);
  }
  while (index < intervals.length && intervals[index][0] <= end) {
    start = Math.min(start, intervals[index][0]);
    end = Math.max(end, intervals[index][1]);
    index++;
  }
  result.push([start, end]);
  while (index < intervals.length) {
    result.push(intervals[index++]);
  }
  return result;
}

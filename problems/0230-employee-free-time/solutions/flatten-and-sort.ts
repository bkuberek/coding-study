export function employeeFreeTime(schedule: number[][][]): number[][] {
  // flat() builds a new outer array, so sorting it leaves the input untouched.
  const intervals = schedule.flat().sort((a, b) => a[0] - b[0]);
  const free: number[][] = [];
  let busyUntil = intervals[0][1];
  for (const [start, end] of intervals) {
    if (start > busyUntil) {
      free.push([busyUntil, start]);
    }
    busyUntil = Math.max(busyUntil, end);
  }
  return free;
}

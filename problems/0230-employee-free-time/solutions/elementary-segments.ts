export function employeeFreeTime(schedule: number[][][]): number[][] {
  const intervals = schedule.flat();
  const points = [...new Set(intervals.flat())].sort((a, b) => a - b);
  const free: number[][] = [];
  for (let i = 1; i < points.length; i++) {
    const left = points[i - 1];
    // No interval starts or ends strictly inside (left, right): it is all busy or all free.
    if (!intervals.some(([start, end]) => start <= left && left < end)) {
      free.push([left, points[i]]);
    }
  }
  return free;
}

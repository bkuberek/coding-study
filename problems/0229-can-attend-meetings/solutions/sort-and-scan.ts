export function canAttendMeetings(intervals: number[][]): boolean {
  const ordered = [...intervals].sort((a, b) => a[0] - b[0]);
  // After sorting by start, only neighbors can be the first clash.
  for (let i = 1; i < ordered.length; i++) {
    if (ordered[i - 1][1] > ordered[i][0]) {
      return false;
    }
  }
  return true;
}

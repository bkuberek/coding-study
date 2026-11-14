export function minMeetingRooms(intervals: number[][]): number {
  const starts = intervals.map(([start]) => start).sort((a, b) => a - b);
  const ends = intervals.map(([, end]) => end).sort((a, b) => a - b);
  let rooms = 0;
  let ended = 0;
  for (const start of starts) {
    if (ends[ended] <= start) {
      // Some meeting has ended by now: its room is reused.
      ended++;
    } else {
      rooms++;
    }
  }
  return rooms;
}

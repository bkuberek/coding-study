export function canFinish(numCourses: number, prerequisites: number[][]): boolean {
  const unlocks: number[][] = Array.from({ length: numCourses }, () => []);
  const waiting = new Array<number>(numCourses).fill(0); // prerequisites each course still waits for
  for (const [course, before] of prerequisites) {
    unlocks[before].push(course);
    waiting[course]++;
  }
  // An array with a moving head is a queue without the O(n) cost of shift().
  const ready: number[] = [];
  for (let course = 0; course < numCourses; course++) {
    if (waiting[course] === 0) {
      ready.push(course);
    }
  }
  for (let head = 0; head < ready.length; head++) {
    for (const unlocked of unlocks[ready[head]]) {
      waiting[unlocked]--;
      if (waiting[unlocked] === 0) {
        ready.push(unlocked);
      }
    }
  }
  // Courses never queued wait, directly or not, on a cycle.
  return ready.length === numCourses;
}

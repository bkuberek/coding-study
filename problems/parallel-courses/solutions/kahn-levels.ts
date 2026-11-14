export function minimumSemesters(n: number, relations: number[][]): number {
  const unlocks: number[][] = Array.from({ length: n + 1 }, () => []);
  const waiting = new Array<number>(n + 1).fill(0);
  for (const [before, after] of relations) {
    unlocks[before].push(after);
    waiting[after]++;
  }
  let semesterCourses: number[] = [];
  for (let course = 1; course <= n; course++) {
    if (waiting[course] === 0) {
      semesterCourses.push(course);
    }
  }
  let semesters = 0;
  let taken = 0;
  while (semesterCourses.length > 0) {
    semesters++;
    taken += semesterCourses.length;
    const nextSemester: number[] = [];
    for (const course of semesterCourses) {
      for (const unlocked of unlocks[course]) {
        waiting[unlocked]--;
        if (waiting[unlocked] === 0) {
          nextSemester.push(unlocked);
        }
      }
    }
    semesterCourses = nextSemester;
  }
  return taken === n ? semesters : -1;
}

export function minimumSemesters(n: number, relations: number[][]): number {
  const required: number[][] = Array.from({ length: n + 1 }, () => []);
  for (const [before, after] of relations) {
    required[after].push(before);
  }
  const finishedIn = new Array<number>(n + 1).fill(0); // semester a course was taken in; 0 while not taken
  let done = 0;
  let semester = 0;
  while (done < n) {
    semester++;
    // Free courses need every prerequisite finished in an earlier semester.
    const free: number[] = [];
    for (let course = 1; course <= n; course++) {
      if (
        finishedIn[course] === 0 &&
        required[course].every((before) => finishedIn[before] > 0 && finishedIn[before] < semester)
      ) {
        free.push(course);
      }
    }
    if (free.length === 0) {
      return -1;
    }
    for (const course of free) {
      finishedIn[course] = semester;
    }
    done += free.length;
  }
  return semester;
}

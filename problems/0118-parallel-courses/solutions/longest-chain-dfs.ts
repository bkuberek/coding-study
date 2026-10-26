const ON_PATH = -1; // marks a course whose chain length is still being computed

export function minimumSemesters(n: number, relations: number[][]): number {
  const required: number[][] = Array.from({ length: n + 1 }, () => []);
  for (const [before, after] of relations) {
    required[after].push(before);
  }
  // chain[c]: courses on the longest prerequisite chain ending at c; 0 = not computed yet.
  const chain = new Array<number>(n + 1).fill(0);
  // Longest chain ending at course, or -1 if its prerequisites loop.
  const chainLength = (course: number): number => {
    if (chain[course] === ON_PATH) {
      return -1;
    }
    if (chain[course] > 0) {
      return chain[course];
    }
    chain[course] = ON_PATH;
    let longest = 0;
    for (const before of required[course]) {
      const length = chainLength(before);
      if (length < 0) {
        return -1;
      }
      longest = Math.max(longest, length);
    }
    chain[course] = longest + 1;
    return chain[course];
  };
  let semesters = 0;
  for (let course = 1; course <= n; course++) {
    const length = chainLength(course);
    if (length < 0) {
      return -1;
    }
    semesters = Math.max(semesters, length);
  }
  return semesters;
}

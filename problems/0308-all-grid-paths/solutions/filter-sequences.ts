export function allGridPaths(n: number): string[] {
  const steps = 2 * (n - 1);
  const paths: string[] = [];
  // Counting up from 0 reads the bits from the most significant one as the first move, with
  // 0 for D and 1 for R, so the sequences come out in lexicographic order.
  for (let pattern = 0; pattern < 1 << steps; pattern++) {
    let moves = "";
    let rights = 0;
    for (let step = 0; step < steps; step++) {
      const isRight = (pattern >> (steps - 1 - step)) & 1;
      moves += isRight ? "R" : "D";
      rights += isRight;
    }
    if (rights === n - 1) {
      paths.push(moves);
    }
  }
  return paths;
}

export function allGridPaths(n: number): string[] {
  const last = n - 1;
  const paths: string[] = [];
  const moves: string[] = [];
  const extend = (downs: number, rights: number): void => {
    if (downs === last && rights === last) {
      paths.push(moves.join(""));
      return;
    }
    // D is tried before R, so the paths come out in lexicographic order.
    if (downs < last) {
      moves.push("D");
      extend(downs + 1, rights);
      moves.pop();
    }
    if (rights < last) {
      moves.push("R");
      extend(downs, rights + 1);
      moves.pop();
    }
  };
  extend(0, 0);
  return paths;
}

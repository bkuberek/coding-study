export function lampPatterns(n: number): string[] {
  const result: string[] = [];
  const lamps: string[] = [];
  const extend = (): void => {
    if (lamps.length === n) {
      result.push(lamps.join(""));
      return;
    }
    lamps.push("0"); // choose: off
    extend(); // explore
    lamps.pop(); // undo
    // Prune: a lamp may be on only when its left neighbour is off (or missing).
    if (lamps.length === 0 || lamps[lamps.length - 1] === "0") {
      lamps.push("1");
      extend();
      lamps.pop();
    }
  };
  extend();
  return result;
}

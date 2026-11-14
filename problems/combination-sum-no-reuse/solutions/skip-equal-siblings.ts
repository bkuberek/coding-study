export function combinationSum2(candidates: number[], target: number): number[][] {
  const ordered = [...candidates].sort((a, b) => a - b);
  const result: number[][] = [];
  const chosen: number[] = [];
  const extend = (start: number, remaining: number): void => {
    if (remaining === 0) {
      result.push([...chosen]);
      return;
    }
    for (let i = start; i < ordered.length && ordered[i] <= remaining; i++) {
      // A second copy at the same level would rebuild the first copy's combinations.
      if (i > start && ordered[i] === ordered[i - 1]) {
        continue;
      }
      chosen.push(ordered[i]);
      extend(i + 1, remaining - ordered[i]);
      chosen.pop();
    }
  };
  extend(0, target);
  return result;
}

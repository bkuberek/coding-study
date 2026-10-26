export function subsetsWithDup(nums: number[]): number[][] {
  const ordered = [...nums].sort((a, b) => a - b);
  const result: number[][] = [];
  const chosen: number[] = [];
  const extend = (start: number): void => {
    // Every node of this recursion is a distinct subset.
    result.push([...chosen]);
    for (let i = start; i < ordered.length; i++) {
      // A second copy at the same level would rebuild the first copy's subtree.
      if (i > start && ordered[i] === ordered[i - 1]) {
        continue;
      }
      chosen.push(ordered[i]);
      extend(i + 1);
      chosen.pop();
    }
  };
  extend(0);
  return result;
}

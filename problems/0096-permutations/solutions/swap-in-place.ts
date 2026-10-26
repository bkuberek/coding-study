export function permute(nums: number[]): number[][] {
  const values = [...nums];
  const result: number[][] = [];
  const swap = (i: number, j: number): void => {
    [values[i], values[j]] = [values[j], values[i]];
  };
  // values[0..slot-1] is the fixed prefix; values[slot..] are the candidates still free.
  const fixSlot = (slot: number): void => {
    if (slot === values.length) {
      result.push([...values]);
      return;
    }
    for (let candidate = slot; candidate < values.length; candidate++) {
      swap(slot, candidate);
      fixSlot(slot + 1);
      swap(slot, candidate);
    }
  };
  fixSlot(0);
  return result;
}

export function findKthLargest(nums: number[], k: number): number {
  const values = [...nums];
  const target = values.length - k; // the answer's index in ascending order
  let low = 0;
  let high = values.length - 1;
  for (;;) {
    const pivot = values[low + Math.floor(Math.random() * (high - low + 1))];
    // Three-way partition of values[low..high]: < pivot | == pivot | > pivot.
    let less = low;
    let scan = low;
    let greater = high;
    while (scan <= greater) {
      if (values[scan] < pivot) {
        [values[less], values[scan]] = [values[scan], values[less]];
        less++;
        scan++;
      } else if (values[scan] > pivot) {
        [values[scan], values[greater]] = [values[greater], values[scan]];
        greater--;
      } else {
        scan++;
      }
    }
    if (target < less) {
      high = less - 1;
    } else if (target > greater) {
      low = greater + 1;
    } else {
      return pivot;
    }
  }
}

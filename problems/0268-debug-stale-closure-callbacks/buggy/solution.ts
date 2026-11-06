// Debug: Stale Closure Callbacks. Some tests fail: find the bugs and fix them.

export function notifyAfterCommit(orderIds: string[], batchSize: number): string[] {
  const afterCommit: Array<() => string> = [];
  let batch: string[] = [];
  let batchNumber = 0;

  for (var row = 1; row <= orderIds.length; row++) {
    batch.push(orderIds[row - 1]);
    if (batch.length === batchSize || row === orderIds.length) {
      batchNumber += 1;
      afterCommit.push(() => `batch ${batchNumber}: ${batch.join("+")} through row ${row}`);
      batch = [];
    }
  }

  // The commit: the transaction is durable, so the callbacks may run now.
  return afterCommit.map((callback) => callback());
}

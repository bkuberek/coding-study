export function notifyAfterCommit(orderIds: string[], batchSize: number): string[] {
  const afterCommit: Array<() => string> = [];
  let batch: string[] = [];
  let batchNumber = 0;

  for (let row = 1; row <= orderIds.length; row++) {
    batch.push(orderIds[row - 1]);
    if (batch.length === batchSize || row === orderIds.length) {
      batchNumber += 1;
      // A closure captures variables, so give each callback constants of its own.
      const number = batchNumber;
      const ids = batch;
      afterCommit.push(() => `batch ${number}: ${ids.join("+")} through row ${row}`);
      batch = [];
    }
  }

  // The commit: the transaction is durable, so the callbacks may run now.
  return afterCommit.map((callback) => callback());
}

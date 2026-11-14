export function getImportance(employees: number[][], employeeId: number): number {
  let total = 0;
  const pending = [employeeId];
  while (pending.length > 0) {
    const wanted = pending.pop() as number;
    // No index: find the record by scanning the whole list.
    const record = employees.find((candidate) => candidate[0] === wanted) as number[];
    total += record[1];
    for (let i = 2; i < record.length; i++) {
      pending.push(record[i]);
    }
  }
  return total;
}

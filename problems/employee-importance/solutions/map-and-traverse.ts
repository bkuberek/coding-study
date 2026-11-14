export function getImportance(employees: number[][], employeeId: number): number {
  const byId = new Map(employees.map((record) => [record[0], record]));
  let total = 0;
  const pending = [employeeId];
  while (pending.length > 0) {
    const record = byId.get(pending.pop() as number) as number[];
    total += record[1];
    // Subordinates start at index 2 of the record.
    for (let i = 2; i < record.length; i++) {
      pending.push(record[i]);
    }
  }
  return total;
}

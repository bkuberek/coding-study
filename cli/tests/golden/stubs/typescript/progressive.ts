// In-Memory Database. Statement: .statements/in-memory-db.md. Run: cstudy test in-memory-db
export class InMemoryDb {
  constructor() {}

  // Level 1
  set(timestamp: number, key: string, field: string, value: string): void {
    throw new Error("Not implemented");
  }

  // Level 1
  get(timestamp: number, key: string, field: string): string {
    throw new Error("Not implemented");
  }

  // Level 2
  scanByPrefix(timestamp: number, key: string, prefix: string): string[] {
    throw new Error("Not implemented");
  }
}

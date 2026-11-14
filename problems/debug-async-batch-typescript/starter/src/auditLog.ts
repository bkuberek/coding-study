// The audit trail. An entry takes 50 ms to reach it.

const RECORD_MS = 50;

export class AuditLog {
  readonly #entries: string[] = [];

  async record(entry: string): Promise<void> {
    await new Promise((resolve) => setTimeout(resolve, RECORD_MS));
    this.#entries.push(entry);
  }

  entries(): string[] {
    return [...this.#entries];
  }
}

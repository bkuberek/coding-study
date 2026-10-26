// Bounded Blocking Queue. Statement: .statements/bounded-blocking-queue.md. Run: cstudy test bounded-blocking-queue
// Concurrency: async
export class BoundedBlockingQueue {
  constructor(capacity: number) {}

  async put(value: number): Promise<void> {
    throw new Error("Not implemented");
  }

  async take(): Promise<number> {
    throw new Error("Not implemented");
  }

  size(): number {
    throw new Error("Not implemented");
  }
}

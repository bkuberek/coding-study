// The entry class: `cstudy` loads `Inbox` from `src/inbox.ts` and grades it on the virtual clock.

export class Inbox {
  publish(body: string): number {
    throw new Error("Not implemented");
  }

  receive(waitMs: number): Promise<string> {
    throw new Error("Not implemented");
  }

  sleep(ms: number): Promise<number> {
    throw new Error("Not implemented");
  }

  steps(count: number, ms: number): Promise<number[]> {
    throw new Error("Not implemented");
  }

  race(names: string): Promise<string> {
    throw new Error("Not implemented");
  }

  hold(): Promise<string> {
    throw new Error("Not implemented");
  }

  spin(): string {
    throw new Error("Not implemented");
  }

  leave(): void {
    throw new Error("Not implemented");
  }
}

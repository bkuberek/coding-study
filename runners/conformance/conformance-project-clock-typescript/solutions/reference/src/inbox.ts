// The entry class: `cstudy` loads `Inbox` from `src/inbox.ts` and grades it on the virtual clock.
//
// `receive` waits on `setTimeout`, and `sleep`, `steps` and `race` on the static import of
// `node:timers/promises`, which the clock's mocks reach; `steps` chains its sleeps, so each one
// starts from the time the one before it ended. `hold`, `spin` and `leave` exist for the runner's
// conformance: `hold` waits on a promise nobody settles (a deadlock), `spin` never returns (a
// wait the clock cannot see), and `leave` leaves a promise and a timer pending.

import { setTimeout as sleepFor } from "node:timers/promises";

const RACE_DELAY_MS = 10;
const LEFT_BEHIND_MS = 1_000_000;

export class Inbox {
  readonly #messages: string[] = [];
  readonly #waiters: ((body: string) => void)[] = [];
  #published = 0;

  publish(body: string): number {
    const waiter = this.#waiters.shift();
    if (waiter === undefined) {
      this.#messages.push(body);
    } else {
      waiter(body);
    }
    this.#published += 1;
    return this.#published;
  }

  receive(waitMs: number): Promise<string> {
    const body = this.#messages.shift();
    if (body !== undefined) {
      return Promise.resolve(body);
    }
    return new Promise((resolve) => {
      const waiter = (message: string): void => {
        clearTimeout(timer);
        resolve(message);
      };
      const timer = setTimeout(() => {
        this.#waiters.splice(this.#waiters.indexOf(waiter), 1);
        resolve("");
      }, waitMs);
      this.#waiters.push(waiter);
    });
  }

  async sleep(ms: number): Promise<number> {
    const start = Date.now();
    await sleepFor(ms);
    return Date.now() - start;
  }

  async steps(count: number, ms: number): Promise<number[]> {
    const ended: number[] = [];
    for (let step = 0; step < count; step++) {
      await sleepFor(ms);
      ended.push(Date.now());
    }
    return ended;
  }

  async race(names: string): Promise<string> {
    const woke: string[] = [];
    await Promise.all(
      [...names].map(async (name) => {
        await sleepFor(RACE_DELAY_MS);
        woke.push(name);
      }),
    );
    return woke.join("");
  }

  hold(): Promise<string> {
    return new Promise(() => {});
  }

  spin(): string {
    for (;;) {
      // never returns
    }
  }

  leave(): void {
    void this.hold();
    setTimeout(() => {}, LEFT_BEHIND_MS);
  }
}

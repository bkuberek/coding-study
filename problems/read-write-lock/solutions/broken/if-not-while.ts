export class ReadWriteLock {
  #readers = 0;
  #writing = false;
  #waitingWriters = 0;
  #waiting: (() => void)[] = [];

  async acquireRead(): Promise<void> {
    while (this.#writing || this.#waitingWriters > 0) {
      await this.#changed();
    }
    this.#readers++;
  }

  releaseRead(): void {
    this.#readers--;
    if (this.#readers === 0) {
      this.#wakeAll();
    }
  }

  async acquireWrite(): Promise<void> {
    this.#waitingWriters++;
    if (this.#writing || this.#readers > 0) {
      await this.#changed();
    }
    this.#waitingWriters--;
    this.#writing = true;
  }

  releaseWrite(): void {
    this.#writing = false;
    this.#wakeAll();
  }

  tryAcquireRead(): boolean {
    if (this.#writing || this.#waitingWriters > 0) {
      return false;
    }
    this.#readers++;
    return true;
  }

  tryAcquireWrite(): boolean {
    if (this.#writing || this.#readers > 0) {
      return false;
    }
    this.#writing = true;
    return true;
  }

  #changed(): Promise<void> {
    return new Promise((resolve) => this.#waiting.push(resolve));
  }

  #wakeAll(): void {
    const waiting = this.#waiting;
    this.#waiting = [];
    for (const resolve of waiting) {
      resolve();
    }
  }
}

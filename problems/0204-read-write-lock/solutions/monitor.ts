export class ReadWriteLock {
  #readers = 0;
  #writing = false;
  readonly #waitingReaders: (() => void)[] = [];
  readonly #waitingWriters: (() => void)[] = [];

  async acquireRead(): Promise<void> {
    if (this.tryAcquireRead()) {
      return;
    }
    await new Promise<void>((resolve) => this.#waitingReaders.push(resolve));
  }

  releaseRead(): void {
    this.#readers--;
    if (this.#readers === 0) {
      this.#admitWriter();
    }
  }

  async acquireWrite(): Promise<void> {
    if (this.tryAcquireWrite()) {
      return;
    }
    await new Promise<void>((resolve) => this.#waitingWriters.push(resolve));
  }

  releaseWrite(): void {
    this.#writing = false;
    if (!this.#admitWriter()) {
      this.#admitReaders();
    }
  }

  tryAcquireRead(): boolean {
    if (this.#writing || this.#waitingWriters.length > 0) {
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

  #admitWriter(): boolean {
    const next = this.#waitingWriters.shift();
    if (next === undefined) {
      return false;
    }
    this.#writing = true;
    next();
    return true;
  }

  #admitReaders(): void {
    const admitted = this.#waitingReaders.splice(0);
    this.#readers += admitted.length;
    for (const resolve of admitted) {
      resolve();
    }
  }
}

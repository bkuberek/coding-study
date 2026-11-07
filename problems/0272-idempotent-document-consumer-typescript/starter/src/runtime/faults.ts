// Switches a test flips to make the world fail on cue. A production build would have none of this.

/** Stands for `kill -9`: in real life no code could catch it, so a broad `catch` must let it pass. */
export class ProcessCrash extends Error {
  constructor(point: string) {
    super(`process crashed at ${point}`);
    this.name = "ProcessCrash";
  }
}

export class Faults {
  #crashPoint: string | null = null;
  #extractionFailures = 0;

  /** The next time execution reaches `point`, the process dies there. One crash per call. */
  armCrash(point: string): void {
    this.#crashPoint = point;
  }

  crashIfArmed(point: string): void {
    if (this.#crashPoint === point) {
      this.#crashPoint = null;
      throw new ProcessCrash(point);
    }
  }

  /** The next `times` extractions fail, whatever their text. */
  failExtractions(times: number): void {
    this.#extractionFailures = times;
  }

  takeExtractionFailure(): boolean {
    if (this.#extractionFailures === 0) {
      return false;
    }
    this.#extractionFailures -= 1;
    return true;
  }
}

// The expensive step: reading a scan. In production this is a paid call, billed per page.

import type { Faults } from "../runtime/faults.ts";

export interface Extraction {
  pages: number;
  words: number;
}

/** Extraction failed. It may work next time, or it may never work. */
export class ExtractionFailed extends Error {
  constructor(reason: string) {
    super(`extraction failed: ${reason}`);
    this.name = "ExtractionFailed";
  }
}

const PAGE_BREAK = "|";
const CORRUPT_HEADER = "%%";

export class Extractor {
  readonly #faults: Faults;

  constructor(faults: Faults) {
    this.#faults = faults;
  }

  extract(body: string): Extraction {
    if (this.#faults.takeExtractionFailure()) {
      throw new ExtractionFailed("service unavailable");
    }
    if (body.startsWith(CORRUPT_HEADER)) {
      throw new ExtractionFailed("corrupt header");
    }
    const pages = body.split(PAGE_BREAK);
    const words = pages.flatMap((page) => page.split(/\s+/)).filter((word) => word !== "");
    return { pages: pages.length, words: words.length };
  }
}

// The consumer's database, in memory. It outlives the process: a restart does not clear it.

import type { Extraction } from "../extraction/extractor.ts";
import type { Faults } from "../runtime/faults.ts";

export interface DocumentRow {
  documentId: string;
  revision: number;
  pipelineVersion: number;
  pages: number;
  words: number;
}

export interface LedgerRow {
  documentId: string;
  pipelineVersion: number;
  pages: number;
}

export interface Tables {
  documents: Map<string, DocumentRow>;
  ledger: LedgerRow[];
  /** Work already paid for, by its key. A row here means: never do this work again. */
  extractions: Map<string, Extraction>;
  deadLetters: string[];
  /** Work given up on, by its key, so a copy of a dead message stays dead. */
  deadKeys: Set<string>;
}

function emptyTables(): Tables {
  return {
    documents: new Map(),
    ledger: [],
    extractions: new Map(),
    deadLetters: [],
    deadKeys: new Set(),
  };
}

export class Database {
  readonly #faults: Faults;
  #tables: Tables = emptyTables();

  constructor(faults: Faults) {
    this.#faults = faults;
  }

  /** Runs a query on the committed tables, which it must not change. */
  read<T>(query: (tables: Readonly<Tables>) => T): T {
    return query(this.#tables);
  }

  /** Runs `work` on a private copy of the tables. When it returns, all of its writes land
   * together. When it throws, none of them do. */
  transaction<T>(work: (tables: Tables) => T): T {
    const draft = structuredClone(this.#tables);
    const result = work(draft);
    this.#faults.crashIfArmed("before-commit");
    this.#tables = draft;
    this.#faults.crashIfArmed("after-commit");
    return result;
  }
}

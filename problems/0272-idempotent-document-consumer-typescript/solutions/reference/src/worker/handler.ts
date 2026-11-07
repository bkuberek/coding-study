// Handles one delivery. The answer goes back to the broker only after the database has the effect.

import { ExtractionFailed } from "../extraction/extractor.ts";
import type { Extraction, Extractor } from "../extraction/extractor.ts";
import type { Database, Tables } from "../storage/database.ts";
import { MalformedDelivery, parseDelivery } from "./delivery.ts";
import type { Delivery } from "./delivery.ts";
import { workKey } from "./workKey.ts";

export type Verdict = "ack" | "retry";

const MAX_DELIVERIES = 3;

/** True when this delivery should replace what the document shows now. */
function supersedes(delivery: Delivery, current: { revision: number; pipelineVersion: number }): boolean {
  if (delivery.revision !== current.revision) {
    return delivery.revision > current.revision;
  }
  return delivery.pipelineVersion > current.pipelineVersion;
}

function publish(tables: Tables, delivery: Delivery, extraction: Extraction): void {
  const { documentId, revision, pipelineVersion } = delivery;
  const { pages, words } = extraction;
  tables.documents.set(documentId, { documentId, revision, pipelineVersion, pages, words });
}

function charge(tables: Tables, delivery: Delivery, extraction: Extraction): void {
  const { documentId, pipelineVersion } = delivery;
  tables.ledger.push({ documentId, pipelineVersion, pages: extraction.pages });
}

export class DeliveryHandler {
  readonly #extractor: Extractor;
  readonly #database: Database;

  constructor(extractor: Extractor, database: Database) {
    this.#extractor = extractor;
    this.#database = database;
  }

  handle(text: string): Verdict {
    let delivery: Delivery;
    try {
      delivery = parseDelivery(text);
    } catch (error) {
      if (error instanceof MalformedDelivery) {
        return this.#deadLetter(`malformed ${text}`, null);
      }
      throw error;
    }

    const key = workKey(delivery.body, delivery.pipelineVersion);
    const current = this.#database.read((tables) => tables.documents.get(delivery.documentId));
    if (current !== undefined && !supersedes(delivery, current)) {
      return "ack";
    }
    if (this.#database.read((tables) => tables.deadKeys.has(key))) {
      return "ack";
    }
    const known = this.#database.read((tables) => tables.extractions.get(key));
    if (known !== undefined) {
      this.#database.transaction((tables) => publish(tables, delivery, known));
      return "ack";
    }
    if (delivery.deliveryCount > MAX_DELIVERIES) {
      return this.#deadLetter(`retries_exhausted ${text}`, key);
    }

    let extraction: Extraction;
    try {
      extraction = this.#extractor.extract(delivery.body);
    } catch (error) {
      if (!(error instanceof ExtractionFailed)) {
        throw error;
      }
      if (delivery.deliveryCount < MAX_DELIVERIES) {
        return "retry";
      }
      return this.#deadLetter(`retries_exhausted ${text}`, key);
    }

    this.#database.transaction((tables) => {
      tables.extractions.set(key, extraction);
      charge(tables, delivery, extraction);
      publish(tables, delivery, extraction);
    });
    return "ack";
  }

  #deadLetter(entry: string, key: string | null): Verdict {
    this.#database.transaction((tables) => {
      tables.deadLetters.push(entry);
      if (key !== null) {
        tables.deadKeys.add(key);
      }
    });
    return "ack";
  }
}

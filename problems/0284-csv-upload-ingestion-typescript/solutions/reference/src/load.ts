// Loads a delivery file's rows into `products`, on the connection of the import's transaction.
// Rows go in batches, a few thousand lines at a time, so a file of any length holds one batch in
// memory and takes one statement per batch, not per row.

import type { PoolClient } from "pg";

import { HEADER, type Row, checked } from "./rows.ts";

export type Outcome = {
  status: "loaded" | "rejected";
  rows: number;
  loaded: number;
  rejected: number;
  report: string[];
};

const REPORT_HEADER = "line,error";
const BATCH_LINES = 5000;

const BAD_HEADER: Outcome = {
  status: "rejected",
  rows: 0,
  loaded: 0,
  rejected: 0,
  report: [REPORT_HEADER, "1,invalid_header"],
};

// One statement per batch. `ON CONFLICT DO UPDATE` may change a row once per statement, so a
// batch holds each SKU once: its quantities summed, and the description of its last line.
const UPSERT = `
  INSERT INTO products (sku, description, quantity)
  SELECT * FROM unnest($1::text[], $2::text[], $3::bigint[])
  ON CONFLICT (sku) DO UPDATE
  SET description = excluded.description, quantity = products.quantity + excluded.quantity`;

class Batch {
  #rows = new Map<string, Row>();
  #lines = 0;

  add(row: Row): void {
    const earlier = this.#rows.get(row.sku);
    this.#rows.set(row.sku, { ...row, quantity: row.quantity + (earlier?.quantity ?? 0) });
    this.#lines += 1;
  }

  get full(): boolean {
    return this.#lines >= BATCH_LINES;
  }

  async flush(client: PoolClient): Promise<void> {
    if (this.#rows.size === 0) {
      return;
    }
    const rows = [...this.#rows.values()];
    await client.query(UPSERT, [
      rows.map((row) => row.sku),
      rows.map((row) => row.description),
      rows.map((row) => row.quantity),
    ]);
    this.#rows.clear();
    this.#lines = 0;
  }
}

// A file is mostly bad when more than half of its rows break a rule: then none of it loads.
function mostlyBad(rows: number, rejected: number): boolean {
  return rejected * 2 > rows;
}

export async function loadFile(client: PoolClient, lines: AsyncIterable<string>): Promise<Outcome> {
  const report = [REPORT_HEADER];
  const batch = new Batch();
  let lineNumber = 0;
  await client.query("SAVEPOINT rows");
  for await (const line of lines) {
    lineNumber += 1;
    if (lineNumber === 1) {
      if (line !== HEADER) {
        return BAD_HEADER;
      }
      continue;
    }
    const row = checked(line);
    if (typeof row === "string") {
      report.push(`${lineNumber},${row}`);
      continue;
    }
    batch.add(row);
    if (batch.full) {
      await batch.flush(client);
    }
  }
  if (lineNumber === 0) {
    return BAD_HEADER;
  }
  await batch.flush(client);
  const rows = lineNumber - 1;
  const rejected = report.length - 1;
  if (mostlyBad(rows, rejected)) {
    await client.query("ROLLBACK TO SAVEPOINT rows");
    return { status: "rejected", rows, loaded: 0, rejected, report };
  }
  return { status: "loaded", rows, loaded: rows - rejected, rejected, report };
}

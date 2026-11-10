// The balance projection made again from the events alone. It runs when the service starts, so the
// projection begins from the history the store already holds, and on demand. One transaction: a
// reader waits for it and never sees the projection half made.

import { inTransaction } from "./db.ts";
import { type Account, type LedgerEvent, evolve, unopened } from "./events.ts";

type StoredEvent = LedgerEvent & { stream_id: string };

export async function rebuild(): Promise<void> {
  await inTransaction(async (connection) => {
    await connection.query("TRUNCATE accounts");
    const found = await connection.query<StoredEvent>(
      "SELECT stream_id, type, data FROM events ORDER BY stream_id, version",
    );
    const accounts = new Map<string, Account>();
    for (const event of found.rows) {
      const state = accounts.get(event.stream_id) ?? unopened(event.stream_id);
      accounts.set(event.stream_id, evolve(state, event));
    }
    const rows = [...accounts.values()];
    await connection.query(
      `INSERT INTO accounts (account, balance, version)
       SELECT * FROM unnest($1::text[], $2::bigint[], $3::integer[])`,
      [rows.map((row) => row.account), rows.map((row) => row.balance), rows.map((row) => row.version)],
    );
  });
}

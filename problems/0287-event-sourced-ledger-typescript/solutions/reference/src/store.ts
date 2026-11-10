// The event store and the balance projection, as the commands and queries read and write them.
// Writes happen inside the caller's transaction, so an event and the projection it moves are
// committed together or not at all.

import type { Connection, Queryable } from "./db.ts";
import { type Account, type LedgerEvent, evolve } from "./events.ts";

type AccountRow = { balance: string; version: number };

// The account as the projection has it, or nothing for an account with no events.
export async function current(db: Queryable, account: string): Promise<Account | undefined> {
  const found = await db.query<AccountRow>(
    "SELECT balance, version FROM accounts WHERE account = $1",
    [account],
  );
  const row = found.rows[0];
  if (row === undefined) {
    return undefined;
  }
  return { account, balance: Number(row.balance), version: row.version };
}

// Whether the account's stream already holds an event with this id: a command that carries it
// again is a replay.
export async function holds(connection: Connection, account: string, eventId: string): Promise<boolean> {
  const found = await connection.query(
    "SELECT 1 FROM events WHERE stream_id = $1 AND event_id = $2",
    [account, eventId],
  );
  return found.rows.length > 0;
}

// Appends `event` as the version after `state`'s, and moves the projection to what `evolve` says.
// If another transaction appended that version first, the unique index refuses the insert, and the
// caller's transaction keeps nothing of this attempt.
export async function append(
  connection: Connection,
  state: Account,
  eventId: string,
  event: LedgerEvent,
): Promise<Account> {
  const next = evolve(state, event);
  await connection.query(
    "INSERT INTO events (stream_id, version, event_id, type, data) VALUES ($1, $2, $3, $4, $5)",
    [next.account, next.version, eventId, event.type, event.data],
  );
  await connection.query(
    `INSERT INTO accounts (account, balance, version) VALUES ($1, $2, $3)
     ON CONFLICT (account) DO UPDATE SET balance = excluded.balance, version = excluded.version`,
    [next.account, next.balance, next.version],
  );
  return next;
}

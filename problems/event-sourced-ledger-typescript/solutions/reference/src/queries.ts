// What the service reads: an account now, from the projection; an account in the past, folded from
// the events recorded by then, since the projection only knows now; and a stream's events.

import { type Answer, invalidRequest, ok, unknownAccount } from "./answers.ts";
import { pool } from "./db.ts";
import { type LedgerEvent, fold } from "./events.ts";
import { instant } from "./requests.ts";
import { current } from "./store.ts";

export async function balance(account: string, query: URLSearchParams): Promise<Answer> {
  const asOf = query.get("as_of");
  if (asOf !== null) {
    return balanceAsOf(account, asOf);
  }
  const state = await current(pool, account);
  return state === undefined ? unknownAccount : ok(state);
}

export async function events(account: string): Promise<Answer> {
  const found = await pool.query(
    "SELECT version, type, data FROM events WHERE stream_id = $1 ORDER BY version",
    [account],
  );
  return found.rows.length === 0 ? unknownAccount : ok(found.rows);
}

async function balanceAsOf(account: string, text: string): Promise<Answer> {
  const moment = instant(text);
  if (moment === undefined) {
    return invalidRequest;
  }
  const found = await pool.query<LedgerEvent>(
    "SELECT type, data FROM events WHERE stream_id = $1 AND recorded_at <= $2 ORDER BY version",
    [account, moment],
  );
  return found.rows.length === 0 ? unknownAccount : ok(fold(account, found.rows));
}

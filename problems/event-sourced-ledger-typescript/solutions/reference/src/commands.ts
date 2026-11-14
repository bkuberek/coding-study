// The three commands. Each reads the account as the projection has it, decides, and appends at the
// next version. Nothing is locked: when another append got that version first, the unique index
// refuses this one and `untilAppended` starts the command over, so every decision is made on what
// is committed, and each version is written by exactly one command.

import { randomUUID } from "node:crypto";

import {
  type Answer,
  insufficientFunds,
  invalidRequest,
  ok,
  unknownAccount,
  versionConflict,
} from "./answers.ts";
import { type Connection, untilAppended } from "./db.ts";
import { type Account, type LedgerEvent, unopened } from "./events.ts";
import { type Movement, movement, transfer as transferRequest } from "./requests.ts";
import { append, current, holds } from "./store.ts";

type Leg = { state: Account; event: LedgerEvent };

export async function deposit(account: string, body: unknown): Promise<Answer> {
  const asked = movement(account, body);
  if (asked === undefined) {
    return invalidRequest;
  }
  return untilAppended(async (connection) => {
    const state = (await current(connection, account)) ?? unopened(account);
    const early = await replayOrConflict(connection, asked, state);
    if (early !== undefined) {
      return early;
    }
    const event: LedgerEvent = { type: "deposited", data: { amount: asked.amount } };
    return ok(await append(connection, state, asked.eventId ?? randomUUID(), event), 201);
  });
}

export async function withdraw(account: string, body: unknown): Promise<Answer> {
  const asked = movement(account, body);
  if (asked === undefined) {
    return invalidRequest;
  }
  return untilAppended(async (connection) => {
    const state = await current(connection, account);
    if (state === undefined) {
      return unknownAccount;
    }
    const early = await replayOrConflict(connection, asked, state);
    if (early !== undefined) {
      return early;
    }
    if (state.balance < asked.amount) {
      return insufficientFunds;
    }
    const event: LedgerEvent = { type: "withdrawn", data: { amount: asked.amount } };
    return ok(await append(connection, state, asked.eventId ?? randomUUID(), event), 201);
  });
}

// Both legs in one transaction: if either append loses its race, neither is kept.
export async function transfer(body: unknown): Promise<Answer> {
  const asked = transferRequest(body);
  if (asked === undefined) {
    return invalidRequest;
  }
  return untilAppended(async (connection) => {
    const from = await current(connection, asked.from);
    const to = await current(connection, asked.to);
    if (from === undefined || to === undefined) {
      return unknownAccount;
    }
    if (asked.eventId !== undefined && (await holds(connection, from.account, asked.eventId))) {
      return ok({ from, to });
    }
    if (from.balance < asked.amount) {
      return insufficientFunds;
    }
    const eventId = asked.eventId ?? randomUUID();
    const legs: Leg[] = [
      { state: from, event: { type: "transferred_out", data: { amount: asked.amount, to: to.account } } },
      { state: to, event: { type: "transferred_in", data: { amount: asked.amount, from: from.account } } },
    ];
    // In account order, whichever way the money goes: two transfers between the same accounts then
    // meet on the same first stream, and one waits for the other instead of each holding a version
    // the other needs.
    const moved = new Map<string, Account>();
    for (const leg of legs.toSorted((a, b) => (a.state.account < b.state.account ? -1 : 1))) {
      moved.set(leg.state.account, await append(connection, leg.state, eventId, leg.event));
    }
    return ok({ from: moved.get(from.account), to: moved.get(to.account) }, 201);
  });
}

// What a deposit or a withdrawal answers instead of appending: a replay answers the account as it
// stands, before any version check, since the command it repeats may be the one that moved the
// version; then a stale expected version is a conflict.
async function replayOrConflict(
  connection: Connection,
  asked: Movement,
  state: Account,
): Promise<Answer | undefined> {
  if (asked.eventId !== undefined && (await holds(connection, state.account, asked.eventId))) {
    return ok(state);
  }
  if (asked.expectedVersion !== undefined && asked.expectedVersion !== state.version) {
    return versionConflict;
  }
  return undefined;
}

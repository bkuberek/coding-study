// Reserving, showing and releasing. Every check that a race could break is made where the race is
// settled: a primary key for an order taken twice, row locks for stock taken at once, and one
// conditional update for a release.

import { type Answer, invalidRequest, ok, refused } from "./answers.ts";
import { type Connection, GiveUp, inTransaction, pool } from "./db.ts";
import { HELD, unknownSku, unknownWarehouse } from "./inventory.ts";
import { type Item, type ReservationRequest, reservationRequest } from "./requests.ts";

type Status = "active" | "released" | "expired";
type Shown = { order: string; status: Status; items: { sku: string; quantity: number }[] };

const orderExists = refused(409, "order_exists");
const insufficientStock = refused(409, "insufficient_stock");
const unknownOrder = refused(404, "unknown_order");
const notActive = refused(409, "not_active");

// An active hold whose time ran out reads as expired; nothing needs to write that down.
const STATUS = `CASE WHEN hold.status = 'active' AND hold.expires_at <= now() THEN 'expired'
                     ELSE hold.status END`;

export async function reserve(body: unknown): Promise<Answer> {
  const asked = reservationRequest(body);
  if (asked === undefined) {
    return invalidRequest;
  }
  const unknown = await unknownPlace(asked.items);
  if (unknown !== undefined) {
    return unknown;
  }
  return inTransaction(async (connection) => {
    await claimOrder(connection, asked);
    await takeStock(connection, asked.items);
    for (const item of asked.items) {
      await connection.query(
        "INSERT INTO reservation_items (order_id, sku, quantity, warehouse) VALUES ($1, $2, $3, $4)",
        [asked.order, item.sku, item.quantity, item.warehouse],
      );
    }
    return ok(shown(asked.order, "active", asked.items), 201);
  });
}

export async function reservation(order: string): Promise<Answer> {
  const found = await pool.query<{ status: Status }>(
    `SELECT ${STATUS} AS status FROM reservations AS hold WHERE hold.order_id = $1`,
    [order],
  );
  const row = found.rows[0];
  return row === undefined ? unknownOrder : ok(shown(order, row.status, await itemsOf(order)));
}

// One statement decides it: of many releases at once, the first to update the row wins, and the
// others find it no longer active.
export async function release(order: string): Promise<Answer> {
  const released = await pool.query(
    `UPDATE reservations SET status = 'released'
     WHERE order_id = $1 AND status = 'active' AND expires_at > now()`,
    [order],
  );
  if (released.rowCount === 1) {
    return ok(shown(order, "released", await itemsOf(order)));
  }
  const known = await pool.query("SELECT 1 FROM reservations WHERE order_id = $1", [order]);
  return known.rowCount === 0 ? unknownOrder : notActive;
}

async function unknownPlace(items: Item[]): Promise<Answer | undefined> {
  const skus = items.map((item) => item.sku);
  const warehouses = items.map((item) => item.warehouse);
  const products = await pool.query("SELECT 1 FROM products WHERE sku = ANY($1)", [skus]);
  if (products.rowCount !== new Set(skus).size) {
    return unknownSku;
  }
  const places = await pool.query("SELECT 1 FROM warehouses WHERE code = ANY($1)", [warehouses]);
  return places.rowCount === new Set(warehouses).size ? undefined : unknownWarehouse;
}

// The primary key settles an order sent twice at once: the second insert waits for the first
// transaction, and finds the order taken if that one commits.
async function claimOrder(connection: Connection, asked: ReservationRequest): Promise<void> {
  const claimed = await connection.query(
    `INSERT INTO reservations (order_id, expires_at)
     VALUES ($1, now() + make_interval(secs => $2))
     ON CONFLICT (order_id) DO NOTHING`,
    [asked.order, asked.holdSeconds],
  );
  if (claimed.rowCount === 0) {
    throw new GiveUp(orderExists);
  }
}

// Locks every row the order takes stock from, always in the same order, by product and then
// warehouse, so two orders for the same products in different orders queue instead of
// deadlocking. Only then is what is available read: no one can take it in between.
async function takeStock(connection: Connection, items: Item[]): Promise<void> {
  const places = [...items].sort((a, b) => byText(a.sku, b.sku) || byText(a.warehouse, b.warehouse));
  for (const place of places) {
    await connection.query(
      "SELECT 1 FROM warehouse_stock WHERE warehouse = $1 AND sku = $2 FOR UPDATE",
      [place.warehouse, place.sku],
    );
  }
  for (const item of items) {
    const found = await connection.query<{ available: number }>(
      `WITH ${HELD}
       SELECT (stock.on_hand - coalesce(held.quantity, 0))::int AS available
       FROM warehouse_stock AS stock
       LEFT JOIN held ON held.warehouse = stock.warehouse AND held.sku = stock.sku
       WHERE stock.warehouse = $1 AND stock.sku = $2`,
      [item.warehouse, item.sku],
    );
    if ((found.rows[0]?.available ?? 0) < item.quantity) {
      throw new GiveUp(insufficientStock);
    }
  }
}

async function itemsOf(order: string): Promise<Item[]> {
  const found = await pool.query<Item>(
    "SELECT sku, quantity, warehouse FROM reservation_items WHERE order_id = $1",
    [order],
  );
  return found.rows;
}

// Items are listed by SKU, however the request ordered them.
function shown(order: string, status: Status, items: Item[]): Shown {
  const listed = [...items].sort((a, b) => byText(a.sku, b.sku));
  return { order, status, items: listed.map(({ sku, quantity }) => ({ sku, quantity })) };
}

function byText(a: string, b: string): number {
  if (a === b) {
    return 0;
  }
  return a < b ? -1 : 1;
}

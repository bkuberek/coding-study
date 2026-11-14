// What is available, per product and per warehouse, and stock coming in. Available is what a
// warehouse has on hand minus what active holds keep there: a hold that ran out keeps nothing, so
// expiring one needs no write at all.

import { type Answer, invalidRequest, ok, refused } from "./answers.ts";
import { pool } from "./db.ts";
import { receipt } from "./requests.ts";

// What active holds keep, per warehouse and product, as a common table expression.
export const HELD = `held AS (
  SELECT item.warehouse, item.sku, sum(item.quantity)::int AS quantity
  FROM reservation_items AS item JOIN reservations AS hold USING (order_id)
  WHERE hold.status = 'active' AND hold.expires_at > now()
  GROUP BY item.warehouse, item.sku)`;

export const unknownSku = refused(404, "unknown_sku");
export const unknownWarehouse = refused(404, "unknown_warehouse");

export async function product(sku: string): Promise<Answer> {
  const found = await pool.query<{ sku: string; name: string; available: number }>(
    `WITH ${HELD}
     SELECT product.sku, product.name,
            (SELECT coalesce(sum(on_hand), 0) FROM warehouse_stock WHERE sku = product.sku)::int
            - (SELECT coalesce(sum(quantity), 0) FROM held WHERE sku = product.sku)::int
            AS available
     FROM products AS product WHERE product.sku = $1`,
    [sku],
  );
  const row = found.rows[0];
  return row === undefined ? unknownSku : ok(row);
}

export async function warehousesOf(sku: string): Promise<Answer> {
  const known = await pool.query("SELECT 1 FROM products WHERE sku = $1", [sku]);
  if (known.rowCount === 0) {
    return unknownSku;
  }
  const found = await pool.query<{ warehouse: string; available: number }>(
    `WITH ${HELD}
     SELECT warehouse.code AS warehouse,
            (coalesce(stock.on_hand, 0) - coalesce(held.quantity, 0))::int AS available
     FROM warehouses AS warehouse
     LEFT JOIN warehouse_stock AS stock ON stock.warehouse = warehouse.code AND stock.sku = $1
     LEFT JOIN held ON held.warehouse = warehouse.code AND held.sku = $1
     ORDER BY warehouse.code`,
    [sku],
  );
  return ok(found.rows);
}

export async function receive(warehouse: string, body: unknown): Promise<Answer> {
  const asked = receipt(body);
  if (asked === undefined) {
    return invalidRequest;
  }
  const place = await pool.query("SELECT 1 FROM warehouses WHERE code = $1", [warehouse]);
  if (place.rowCount === 0) {
    return unknownWarehouse;
  }
  const added = await pool.query<{ available: number }>(
    `WITH ${HELD},
     added AS (
       UPDATE warehouse_stock SET on_hand = on_hand + $3
       WHERE warehouse = $1 AND sku = $2 RETURNING on_hand)
     SELECT (added.on_hand - coalesce(
       (SELECT quantity FROM held WHERE warehouse = $1 AND sku = $2), 0))::int AS available
     FROM added`,
    [warehouse, asked.sku, asked.quantity],
  );
  const row = added.rows[0];
  if (row === undefined) {
    return unknownSku;
  }
  return ok({ warehouse, sku: asked.sku, available: row.available }, 201);
}

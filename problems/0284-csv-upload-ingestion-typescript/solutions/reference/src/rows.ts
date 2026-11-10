// The rules of a delivery file: its header, and what each row must hold. A row breaks at most one
// rule, the first in the statement's order.

export const HEADER = "sku,description,quantity";

export type Row = { sku: string; description: string; quantity: number };

export type Rejection =
  | "wrong_column_count"
  | "invalid_sku"
  | "invalid_description"
  | "invalid_quantity";

const COLUMNS = 3;
const SKU = /^[A-Z0-9][A-Z0-9-]{0,31}$/;
const MAX_DESCRIPTION = 300;
const WHOLE_NUMBER = /^[1-9][0-9]*$/;
const MAX_QUANTITY = 100_000;

export function checked(line: string): Row | Rejection {
  const columns = line.split(",");
  if (columns.length !== COLUMNS) {
    return "wrong_column_count";
  }
  const [sku, description, quantity] = columns;
  if (!SKU.test(sku)) {
    return "invalid_sku";
  }
  if (description.length === 0 || description.length > MAX_DESCRIPTION) {
    return "invalid_description";
  }
  if (!WHOLE_NUMBER.test(quantity) || Number(quantity) > MAX_QUANTITY) {
    return "invalid_quantity";
  }
  return { sku, description, quantity: Number(quantity) };
}

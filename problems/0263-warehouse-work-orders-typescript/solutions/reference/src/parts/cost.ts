// What a work order costs. Nothing here is stored: a cost is worked out from the order, its parts
// and its site each time, in whole cents, so it can never disagree with them.

import type { Site } from "../sites/directory.ts";
import type { PartLine } from "./store.ts";

const MINUTES_PER_HOUR = 60;
const BASIS_POINTS = 10000;

export interface OrderCost {
  readonly laborCostCents: number;
  readonly partsCostCents: number;
  readonly totalCostCents: number;
}

export function orderCost(
  order: { readonly laborMinutes: number },
  parts: readonly PartLine[],
  site: Site,
): OrderCost {
  const laborCostCents = dividedHalfUp(order.laborMinutes * site.laborRateCentsPerHour, MINUTES_PER_HOUR);
  const subtotal = parts.reduce((sum, line) => sum + line.quantity * line.unitCostCents, 0);
  const partsCostCents = dividedHalfUp(subtotal * (BASIS_POINTS + site.partsMarkupBasisPoints), BASIS_POINTS);
  return { laborCostCents, partsCostCents, totalCostCents: laborCostCents + partsCostCents };
}

/** `dividend / divisor`, a half rounding up, in integer arithmetic: multiply first, divide last. */
export function dividedHalfUp(dividend: number, divisor: number): number {
  return Math.floor((2 * dividend + divisor) / (2 * divisor));
}

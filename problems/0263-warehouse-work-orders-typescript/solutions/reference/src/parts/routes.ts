// The routes for a work order's parts and its cost.

import { readJsonObject } from "../shared/body.ts";
import { checkIfMatch } from "../shared/preconditions.ts";
import { validationFailed } from "../shared/problems.ts";
import type { FieldProblem } from "../shared/problems.ts";
import type { Route } from "../shared/routing.ts";
import type { Site } from "../sites/directory.ts";
import type { Features } from "../workorders/routes.ts";
import { requireOrder } from "../workorders/routes.ts";
import { MESSAGES, isFilledText } from "../workorders/validate.ts";
import { orderCost } from "./cost.ts";
import type { PartLine } from "./store.ts";

const MAX_QUANTITY = 10000;
const MAX_UNIT_COST_CENTS = 1000000;
const PART_FIELDS = new Set(["sku", "quantity", "unitCostCents"]);

export function partRoutes({ orders, sites, parts }: Features): Route[] {
  return [
    {
      method: "POST",
      pattern: "/work-orders/:id/parts",
      handle: (request) => {
        const order = requireOrder(orders, request);
        checkIfMatch(request, order);
        const line = parts.add(order.id, parsePart(readJsonObject(request.body)));
        orders.touch(order);
        return { status: 201, body: line };
      },
    },
    {
      method: "GET",
      pattern: "/work-orders/:id/cost",
      handle: (request) => {
        const order = requireOrder(orders, request);
        const cost = orderCost(order, parts.forOrder(order.id), sites.get(order.siteId) as Site);
        return { status: 200, body: { workOrderId: order.id, ...cost } };
      },
    },
  ];
}

function parsePart(input: Record<string, unknown>): Pick<PartLine, "sku" | "quantity" | "unitCostCents"> {
  const { sku, quantity, unitCostCents } = input;
  const problems: FieldProblem[] = [];
  if (!isFilledText(sku)) {
    problems.push({ field: "sku", message: MESSAGES.title });
  }
  if (!isWholeBetween(quantity, 1, MAX_QUANTITY)) {
    problems.push({ field: "quantity", message: `must be a whole number from 1 to ${MAX_QUANTITY}` });
  }
  if (!isWholeBetween(unitCostCents, 0, MAX_UNIT_COST_CENTS)) {
    const message = `must be a whole number from 0 to ${MAX_UNIT_COST_CENTS}`;
    problems.push({ field: "unitCostCents", message });
  }
  for (const key of Object.keys(input).sort()) {
    if (!PART_FIELDS.has(key)) {
      problems.push({ field: key, message: MESSAGES.unknownField });
    }
  }
  if (problems.length > 0) {
    throw validationFailed(problems);
  }
  return {
    sku: (sku as string).trim(),
    quantity: quantity as number,
    unitCostCents: unitCostCents as number,
  };
}

function isWholeBetween(value: unknown, min: number, max: number): boolean {
  return Number.isInteger(value) && (value as number) >= min && (value as number) <= max;
}

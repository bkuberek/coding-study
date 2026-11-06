// GET /reports/site-costs: reads every other feature and owns no data of its own. The dependency
// points one way: nothing else imports a report.

import { orderCost } from "../parts/cost.ts";
import { invalidQuery } from "../shared/problems.ts";
import type { Route } from "../shared/routing.ts";
import type { Features } from "../workorders/routes.ts";
import { MESSAGES, isPriority } from "../workorders/validate.ts";

interface Totals {
  orderCount: number;
  laborCostCents: number;
  partsCostCents: number;
  totalCostCents: number;
}

export function reportRoutes({ orders, sites, parts }: Features): Route[] {
  return [
    {
      method: "GET",
      pattern: "/reports/site-costs",
      handle: (request) => {
        const priority = request.query.get("priority");
        if (priority !== null && !isPriority(priority)) {
          throw invalidQuery([{ field: "priority", message: MESSAGES.priority }]);
        }
        const live = orders.list().filter((order) => priority === null || order.priority === priority);
        const totals = emptyTotals();
        // Starting from the sites, not the orders, keeps a site with nothing to report.
        const rows = sites.list().map((site) => {
          const row = emptyTotals();
          for (const order of live.filter((candidate) => candidate.siteId === site.id)) {
            add(row, 1, orderCost(order, parts.forOrder(order.id), site));
          }
          add(totals, row.orderCount, row);
          return { siteId: site.id, siteName: site.name, ...row };
        });
        return { status: 200, body: { sites: rows, totals } };
      },
    },
  ];
}

function emptyTotals(): Totals {
  return { orderCount: 0, laborCostCents: 0, partsCostCents: 0, totalCostCents: 0 };
}

/** Adds costs already rounded per order, so a report always equals the sum of what each order says. */
function add(
  totals: Totals,
  orderCount: number,
  cost: Omit<Totals, "orderCount">,
): void {
  totals.orderCount += orderCount;
  totals.laborCostCents += cost.laborCostCents;
  totals.partsCostCents += cost.partsCostCents;
  totals.totalCostCents += cost.totalCostCents;
}

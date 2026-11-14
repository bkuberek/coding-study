// The routes of /work-orders.

import { readJsonObject } from "../shared/body.ts";
import { notFound } from "../shared/problems.ts";
import type { Route } from "../shared/routing.ts";
import type { SiteDirectory } from "../sites/directory.ts";
import type { WorkOrderStore } from "./store.ts";
import { parseNewWorkOrder } from "./validate.ts";

export function workOrderRoutes(orders: WorkOrderStore, sites: SiteDirectory): Route[] {
  return [
    {
      method: "GET",
      pattern: "/work-orders",
      handle: () => {
        const items = orders.list();
        return { status: 200, body: { items, total: items.length } };
      },
    },
    {
      method: "POST",
      pattern: "/work-orders",
      handle: (request) => {
        const input = parseNewWorkOrder(readJsonObject(request.body), sites);
        return { status: 201, body: orders.create(input) };
      },
    },
    {
      method: "GET",
      pattern: "/work-orders/:id",
      handle: (request) => {
        const order = orders.get(request.params.id);
        if (order === undefined) {
          throw notFound(`No work order ${request.params.id}`);
        }
        return { status: 200, body: order };
      },
    },
  ];
}

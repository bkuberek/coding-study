// The routes of /work-orders.

import type { ReplayCache } from "../idempotency/replayCache.ts";
import type { PartStore } from "../parts/store.ts";
import { readJsonObject } from "../shared/body.ts";
import { checkIfMatch } from "../shared/preconditions.ts";
import { invalidQuery, notFound, validationFailed } from "../shared/problems.ts";
import type { ApiRequest, Answer, Route } from "../shared/routing.ts";
import type { SiteDirectory } from "../sites/directory.ts";
import type { WorkOrder } from "./model.ts";
import type { WorkOrderStore } from "./store.ts";
import { parseChanges, parseNewWorkOrder } from "./validate.ts";

export interface Features {
  readonly orders: WorkOrderStore;
  readonly sites: SiteDirectory;
  readonly parts: PartStore;
}

/** The live order, or the 404 every route under /work-orders/:id answers. */
export function requireOrder(orders: WorkOrderStore, request: ApiRequest): WorkOrder {
  const order = orders.get(request.params.id);
  if (order === undefined) {
    throw notFound(`No work order ${request.params.id}`);
  }
  return order;
}

export function workOrderRoutes(features: Features, replays: ReplayCache): Route[] {
  const { orders, sites } = features;

  const create = (input: Record<string, unknown>): Answer => ({
    status: 201,
    body: orders.create(parseNewWorkOrder(input, sites)),
  });

  return [
    {
      method: "GET",
      pattern: "/work-orders",
      handle: (request) => {
        const items = includesDeleted(request.query) ? orders.listIncludingDeleted() : orders.list();
        return { status: 200, body: { items, total: items.length } };
      },
    },
    {
      method: "POST",
      pattern: "/work-orders",
      handle: (request) => {
        const key = request.headers.get("idempotency-key");
        if (key === "") {
          throw validationFailed([{ field: "Idempotency-Key", message: "must not be blank" }]);
        }
        const input = readJsonObject(request.body);
        if (key === undefined) {
          return create(input);
        }
        const replayed = replays.replay(key, input);
        if (replayed !== undefined) {
          return replayed;
        }
        const answer = create(input);
        replays.remember(key, input, answer);
        return answer;
      },
    },
    {
      method: "GET",
      pattern: "/work-orders/:id",
      handle: (request) => ({ status: 200, body: requireOrder(orders, request) }),
    },
    {
      method: "PATCH",
      pattern: "/work-orders/:id",
      handle: (request) => {
        const order = requireOrder(orders, request);
        checkIfMatch(request, order);
        orders.update(order, parseChanges(readJsonObject(request.body)));
        return { status: 200, body: order };
      },
    },
    {
      method: "DELETE",
      pattern: "/work-orders/:id",
      handle: (request) => {
        const order = requireOrder(orders, request);
        checkIfMatch(request, order);
        orders.delete(order);
        return { status: 200, body: { deleted: true, id: order.id } };
      },
    },
  ];
}

/** Text, so "false" would be truthy: it has to be compared, never tested. */
function includesDeleted(query: URLSearchParams): boolean {
  const value = query.get("includeDeleted");
  if (value !== null && value !== "true" && value !== "false") {
    throw invalidQuery([{ field: "includeDeleted", message: "must be true or false" }]);
  }
  return value === "true";
}

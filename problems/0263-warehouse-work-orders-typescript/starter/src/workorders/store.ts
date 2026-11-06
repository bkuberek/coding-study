// The in-memory table of work orders. The people in it are made up.

import type { NewWorkOrder, WorkOrder } from "./model.ts";

const FIRST_ORDER_NUMBER = 101;

export const SEED_WORK_ORDERS: readonly WorkOrder[] = [
  { id: "WO-101", siteId: "WH-1", title: "Replace dock seal", priority: "high", assignee: "Mo Standin", laborMinutes: 90, version: 1 },
  { id: "WO-102", siteId: "WH-1", title: "Recalibrate floor scale", priority: "normal", assignee: null, laborMinutes: 0, version: 1 },
  { id: "WO-103", siteId: "WH-2", title: "Patch conveyor belt", priority: "low", assignee: "Noa Fakename", laborMinutes: 45, version: 1 },
];

export class WorkOrderStore {
  readonly #orders: WorkOrder[];
  #nextNumber: number;

  constructor(seed: readonly WorkOrder[]) {
    this.#orders = seed.map((order) => ({ ...order }));
    this.#nextNumber = FIRST_ORDER_NUMBER + seed.length;
  }

  list(): readonly WorkOrder[] {
    return this.#orders;
  }

  get(id: string): WorkOrder | undefined {
    return this.#orders.find((order) => order.id === id);
  }

  create(input: NewWorkOrder): WorkOrder {
    const order: WorkOrder = { id: `WO-${this.#nextNumber}`, ...input, version: 1 };
    this.#nextNumber += 1;
    this.#orders.push(order);
    return order;
  }
}

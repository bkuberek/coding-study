// The in-memory table of work orders. The people in it are made up.
//
// A deleted row stays in the table, marked, so the store is the one place that knows the mark
// exists: everything but `listIncludingDeleted` sees only live orders, as a view would show them.

import type { NewWorkOrder, WorkOrder, WorkOrderChanges } from "./model.ts";

const FIRST_ORDER_NUMBER = 101;

export const SEED_WORK_ORDERS: readonly WorkOrder[] = [
  { id: "WO-101", siteId: "WH-1", title: "Replace dock seal", priority: "high", assignee: "Mo Standin", laborMinutes: 90, version: 1 },
  { id: "WO-102", siteId: "WH-1", title: "Recalibrate floor scale", priority: "normal", assignee: null, laborMinutes: 0, version: 1 },
  { id: "WO-103", siteId: "WH-2", title: "Patch conveyor belt", priority: "low", assignee: "Noa Fakename", laborMinutes: 45, version: 1 },
];

interface Row {
  readonly order: WorkOrder;
  deleted: boolean;
}

export class WorkOrderStore {
  readonly #rows: Row[];
  #nextNumber: number;

  constructor(seed: readonly WorkOrder[]) {
    this.#rows = seed.map((order) => ({ order: { ...order }, deleted: false }));
    this.#nextNumber = FIRST_ORDER_NUMBER + seed.length;
  }

  list(): WorkOrder[] {
    return this.#rows.filter((row) => !row.deleted).map((row) => row.order);
  }

  listIncludingDeleted(): Array<WorkOrder & { readonly deleted: boolean }> {
    return this.#rows.map((row) => ({ ...row.order, deleted: row.deleted }));
  }

  get(id: string): WorkOrder | undefined {
    return this.list().find((order) => order.id === id);
  }

  create(input: NewWorkOrder): WorkOrder {
    const order: WorkOrder = { id: `WO-${this.#nextNumber}`, ...input, version: 1 };
    this.#nextNumber += 1;
    this.#rows.push({ order, deleted: false });
    return order;
  }

  /** Applies the changes; the version counts changes, so a request that changes nothing keeps it. */
  update(order: WorkOrder, changes: WorkOrderChanges): void {
    const changed = (Object.keys(changes) as Array<keyof WorkOrderChanges>).some(
      (key) => order[key] !== changes[key],
    );
    if (changed) {
      Object.assign(order, changes);
      order.version += 1;
    }
  }

  /** Something else about the order changed, such as its parts. */
  touch(order: WorkOrder): void {
    order.version += 1;
  }

  delete(order: WorkOrder): void {
    const row = this.#rows.find((candidate) => candidate.order === order);
    if (row !== undefined) {
      row.deleted = true;
      order.version += 1;
    }
  }
}

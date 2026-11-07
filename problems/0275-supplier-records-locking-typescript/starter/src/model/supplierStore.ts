// The suppliers, in memory.

import type { EditableFields, Supplier } from "./supplier.ts";

export const SEED_SUPPLIERS: readonly Supplier[] = [
  {
    id: "S-1",
    name: "Placeholder Parts",
    contactEmail: "orders@parts.example",
    notes: "",
    minOrderCents: 1000,
    maxOrderCents: 50000,
    status: "active",
    version: 1,
  },
  {
    id: "S-2",
    name: "Sample Supply",
    contactEmail: "desk@supply.example",
    notes: "Net 30",
    minOrderCents: 0,
    maxOrderCents: 20000,
    status: "paused",
    version: 1,
  },
];

export class SupplierStore {
  readonly #suppliers = new Map<string, Supplier>();

  constructor(seed: readonly Supplier[]) {
    for (const supplier of seed) {
      this.#suppliers.set(supplier.id, { ...supplier });
    }
  }

  find(id: string): Supplier | undefined {
    return this.#suppliers.get(id);
  }

  /** Every supplier, sorted by id. */
  all(): Supplier[] {
    return [...this.#suppliers.values()].sort((a, b) => (a.id < b.id ? -1 : 1));
  }

  create(id: string, fields: EditableFields): Supplier {
    const supplier = { ...fields, id, version: 1 };
    this.#suppliers.set(id, supplier);
    return supplier;
  }

  update(current: Supplier, fields: EditableFields): Supplier {
    const updated = { ...fields, id: current.id, version: current.version + 1 };
    this.#suppliers.set(current.id, updated);
    return updated;
  }
}

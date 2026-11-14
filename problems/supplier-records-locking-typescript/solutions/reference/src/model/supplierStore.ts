// The suppliers, in memory. A version never goes back, so a deleted supplier stays here as a
// tombstone: its version is what the next supplier with that id continues from.

import { EDITABLE_FIELDS } from "./supplier.ts";
import type { EditableField, EditableFields, Supplier } from "./supplier.ts";

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

interface Entry {
  supplier: Supplier;
  deleted: boolean;
  /** The version at which each field last changed. */
  lastChanged: Map<EditableField, number>;
}

function allChangedAt(version: number): Map<EditableField, number> {
  return new Map(EDITABLE_FIELDS.map((field) => [field, version]));
}

export class SupplierStore {
  readonly #entries = new Map<string, Entry>();

  constructor(seed: readonly Supplier[]) {
    for (const supplier of seed) {
      this.#entries.set(supplier.id, {
        supplier: { ...supplier },
        deleted: false,
        lastChanged: allChangedAt(supplier.version),
      });
    }
  }

  find(id: string): Supplier | undefined {
    const entry = this.#entries.get(id);
    return entry === undefined || entry.deleted ? undefined : entry.supplier;
  }

  /** Every supplier, sorted by id. */
  all(): Supplier[] {
    return [...this.#entries.values()]
      .filter((entry) => !entry.deleted)
      .map((entry) => entry.supplier)
      .sort((a, b) => (a.id < b.id ? -1 : 1));
  }

  lastChanged(id: string, field: EditableField): number {
    return this.#entries.get(id)?.lastChanged.get(field) ?? 0;
  }

  /** A new supplier starts at 1, and one taking a deleted supplier's id continues from it. */
  create(id: string, fields: EditableFields): Supplier {
    const version = (this.#entries.get(id)?.supplier.version ?? 0) + 1;
    const supplier = { ...fields, id, version };
    this.#entries.set(id, { supplier, deleted: false, lastChanged: allChangedAt(version) });
    return supplier;
  }

  /** Writes the fields that differ. A write that changes nothing leaves the version as it is. */
  apply(current: Supplier, fields: Partial<EditableFields>): Supplier {
    const entry = this.#entries.get(current.id);
    const changed = EDITABLE_FIELDS.filter(
      (field) => field in fields && fields[field] !== current[field],
    );
    if (entry === undefined || changed.length === 0) {
      return current;
    }
    const version = current.version + 1;
    entry.supplier = { ...current, ...fields, version };
    for (const field of changed) {
      entry.lastChanged.set(field, version);
    }
    return entry.supplier;
  }

  /** Answers the version the delete took. */
  delete(current: Supplier): number {
    const version = current.version + 1;
    this.#entries.set(current.id, {
      supplier: { ...current, version },
      deleted: true,
      lastChanged: allChangedAt(version),
    });
    return version;
  }
}

// The recorded state maps an address to an id and attributes, and a scan maps an id to a type
// and attributes. Drift is found by looking each recorded id up in the scan, comparing values
// after the type's normalization rules, and filtering the rows through the ignore rules. Import
// adds a recorded entry, the plan compares the desired state with the recorded one, and a
// reconcile turns each drift row into the action of the newest policy that matches.
type Attributes = Map<string, string>;

interface Entry {
  tag: string;
  attributes: Attributes;
}

interface DriftRow {
  row: string[];
  address: string;
}

function compare(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function toMap(attributes: string[][]): Attributes {
  return new Map(attributes.map(([key, value]) => [key, value] as [string, string]));
}

function kindOf(address: string): string {
  return address.slice(0, address.indexOf("."));
}

// Whether `text` matches `pattern`, where `*` stands for any run of characters. On a mismatch,
// go back to the last star and let it swallow one more character.
function glob(pattern: string, text: string): boolean {
  let p = 0;
  let t = 0;
  let star = -1;
  let mark = 0;
  while (t < text.length) {
    if (p < pattern.length && pattern[p] !== "*" && pattern[p] === text[t]) {
      p++;
      t++;
    } else if (p < pattern.length && pattern[p] === "*") {
      star = p;
      mark = t;
      p++;
    } else if (star >= 0) {
      mark++;
      p = star + 1;
      t = mark;
    } else {
      return false;
    }
  }
  while (p < pattern.length && pattern[p] === "*") {
    p++;
  }
  return p === pattern.length;
}

export class DriftDetector {
  private recorded = new Map<string, Entry>();
  private observed = new Map<string, Entry>();
  private ignores = new Set<string>();
  private ignoreRules: Array<[string, string]> = [];
  private lists = new Set<string>();
  private defaults = new Map<string, string>();
  private desired = new Map<string, Attributes>();
  private policies = new Map<string, string>();

  // Level 1
  record(address: string, resourceId: string, attributes: string[][]): boolean {
    const isNew = !this.recorded.has(address);
    this.recorded.set(address, { tag: resourceId, attributes: toMap(attributes) });
    return isNew;
  }

  observe(resourceId: string, resourceType: string, attributes: string[][]): boolean {
    const isNew = !this.observed.has(resourceId);
    this.observed.set(resourceId, { tag: resourceType, attributes: toMap(attributes) });
    return isNew;
  }

  drift(): string[][] {
    return this.driftRows().map((found) => found.row);
  }

  // Level 2
  ignore(pattern: string, key: string): boolean {
    const id = `${pattern}\u0000${key}`;
    if (this.ignores.has(id)) {
      return false;
    }
    this.ignores.add(id);
    this.ignoreRules.push([pattern, key]);
    return true;
  }

  unordered(resourceType: string, key: string): boolean {
    const id = `${resourceType}.${key}`;
    if (this.lists.has(id)) {
      return false;
    }
    this.lists.add(id);
    return true;
  }

  defaultValue(resourceType: string, key: string, value: string): boolean {
    const id = `${resourceType}.${key}`;
    const isNew = !this.defaults.has(id);
    this.defaults.set(id, value);
    return isNew;
  }

  // Level 3
  importResource(address: string, resourceId: string): string {
    const found = this.observed.get(resourceId);
    if (found === undefined) {
      return "not-found";
    }
    if (kindOf(address) !== found.tag) {
      return "type-mismatch";
    }
    for (const entry of this.recorded.values()) {
      if (entry.tag === resourceId) {
        return "already-managed";
      }
    }
    if (this.recorded.has(address)) {
      return "address-taken";
    }
    this.recorded.set(address, { tag: resourceId, attributes: new Map(found.attributes) });
    return "imported";
  }

  desire(address: string, attributes: string[][]): boolean {
    const isNew = !this.desired.has(address);
    this.desired.set(address, toMap(attributes));
    return isNew;
  }

  plan(): string[][] {
    const addresses = [...new Set([...this.desired.keys(), ...this.recorded.keys()])].sort(compare);
    const rows: string[][] = [];
    for (const address of addresses) {
      const entry = this.recorded.get(address);
      const wanted = this.desired.get(address);
      if (entry === undefined) {
        rows.push(["create", address]);
      } else if (wanted === undefined) {
        rows.push(["delete", address]);
      } else {
        for (const key of this.differing(kindOf(address), entry.attributes, wanted)) {
          rows.push(["update", address, key, entry.attributes.get(key) ?? "", wanted.get(key) ?? ""]);
        }
      }
    }
    return rows;
  }

  // Level 4
  policy(pattern: string, mode: string): boolean {
    const isNew = !this.policies.has(pattern);
    this.policies.delete(pattern);
    this.policies.set(pattern, mode);
    return isNew;
  }

  reconcile(): string[][] {
    const rows: string[][] = [];
    for (const { row, address } of this.driftRows()) {
      if (row[0] === "unmanaged") {
        rows.push(["alert-unmanaged", row[1], row[2]]);
        continue;
      }
      const mode = this.mode(address);
      if (row[0] === "deleted") {
        if (mode === "revert") {
          rows.push(["recreate", address]);
        } else if (mode === "accept") {
          rows.push(["forget", address]);
        } else {
          rows.push(["alert-deleted", address, row[2]]);
        }
        continue;
      }
      const [, , key, recorded, scanned] = row;
      if (mode === "alert") {
        rows.push(["alert", address, key, recorded, scanned]);
        continue;
      }
      const desired = this.desired.get(address)?.get(key) ?? "";
      if (this.same(kindOf(address), key, scanned || undefined, desired || undefined)) {
        continue;
      }
      rows.push(
        mode === "revert"
          ? ["revert", address, key, scanned, desired]
          : ["accept", address, key, desired, scanned],
      );
    }
    return rows;
  }

  // Comparing
  private same(
    resourceType: string,
    key: string,
    first: string | undefined,
    second: string | undefined,
  ): boolean {
    const id = `${resourceType}.${key}`;
    const fallback = this.defaults.get(id);
    const a = first ?? fallback;
    const b = second ?? fallback;
    if (a === undefined || b === undefined) {
      return a === b;
    }
    if (this.lists.has(id)) {
      return a.split(",").sort(compare).join(",") === b.split(",").sort(compare).join(",");
    }
    return a === b;
  }

  private differing(resourceType: string, first: Attributes, second: Attributes): string[] {
    return [...new Set([...first.keys(), ...second.keys()])]
      .sort(compare)
      .filter((key) => !this.same(resourceType, key, first.get(key), second.get(key)));
  }

  private ignored(text: string, key: string): boolean {
    return this.ignoreRules.some(([pattern, ruleKey]) => ruleKey === key && glob(pattern, text));
  }

  private mode(address: string): string {
    let mode = "alert";
    for (const [pattern, rule] of this.policies) {
      if (glob(pattern, address)) {
        mode = rule;
      }
    }
    return mode;
  }

  private driftRows(): DriftRow[] {
    const rows: DriftRow[] = [];
    const managed = new Set<string>();
    for (const address of [...this.recorded.keys()].sort(compare)) {
      const entry = this.recorded.get(address)!;
      managed.add(entry.tag);
      if (this.ignored(address, "*")) {
        continue;
      }
      const found = this.observed.get(entry.tag);
      if (found === undefined) {
        rows.push({ row: ["deleted", address, entry.tag], address });
        continue;
      }
      for (const key of this.differing(kindOf(address), entry.attributes, found.attributes)) {
        if (!this.ignored(address, key)) {
          const recorded = entry.attributes.get(key) ?? "";
          const scanned = found.attributes.get(key) ?? "";
          rows.push({ row: ["changed", address, key, recorded, scanned], address });
        }
      }
    }
    for (const resourceId of [...this.observed.keys()].sort(compare)) {
      const resourceType = this.observed.get(resourceId)!.tag;
      if (!managed.has(resourceId) && !this.ignored(`${resourceType}.${resourceId}`, "*")) {
        rows.push({ row: ["unmanaged", resourceId, resourceType], address: "" });
      }
    }
    return rows;
  }
}

import { createHash } from "node:crypto";

const FIXED_SIZE = 64;
const WINDOW = 16;
const BASE = 257;
const MODULUS = 1_000_000_007;
const MIN_CHUNK = 32;
const MAX_CHUNK = 256;
const DIVISOR = 64;
const KINDS = new Set(["blob", "tree", "manifest"]);

type Entry = { kind: string; address: string };

function addressOf(data: Buffer): string {
  return createHash("sha256").update(data).digest("hex");
}

class Damaged extends Error {}

function fixedSizes(length: number): number[] {
  const sizes: number[] = [];
  for (let start = 0; start < length; start += FIXED_SIZE) {
    sizes.push(Math.min(FIXED_SIZE, length - start));
  }
  return sizes;
}

// The weight of the byte that leaves the window: 257^15 mod 1000000007.
function leavingWeight(): number {
  let weight = 1;
  for (let i = 0; i < WINDOW - 1; i++) {
    weight = (weight * BASE) % MODULUS;
  }
  return weight;
}

// Content-defined cuts: a rolling hash of the last 16 bytes, rolled once per byte. Every product
// stays below 2^53, so plain numbers are exact.
function cdcSizes(data: Buffer): number[] {
  const weight = leavingWeight();
  const sizes: number[] = [];
  let windowHash = 0;
  let start = 0;
  for (let index = 0; index < data.length; index++) {
    if (index >= WINDOW) {
      windowHash = (windowHash - ((data[index - WINDOW] * weight) % MODULUS) + MODULUS) % MODULUS;
    }
    windowHash = (windowHash * BASE + data[index]) % MODULUS;
    const length = index - start + 1;
    if (length === MAX_CHUNK || (length >= MIN_CHUNK && windowHash % DIVISOR === 0)) {
      sizes.push(length);
      start = index + 1;
    }
  }
  if (start < data.length) {
    sizes.push(data.length - start);
  }
  return sizes;
}

function lines(text: string): string[] {
  return text === "" ? [] : text.slice(0, -1).split("\n");
}

// Objects are bytes filed under the SHA-256 digest of those bytes. Every read hashes what it finds
// again, so a damaged object reads as a missing one. Folders and manifests are objects that list
// other objects by address, and refs name the objects the collector keeps.
export class ContentStore {
  private readonly objects = new Map<string, Buffer>();
  private readonly fileBytes = new Map<string, number>([
    ["fixed", 0],
    ["cdc", 0],
  ]);
  private readonly chunks = new Map<string, Map<string, number>>([
    ["fixed", new Map()],
    ["cdc", new Map()],
  ]);
  private readonly refs = new Map<string, Entry>();

  private write(data: Buffer): string {
    const address = addressOf(data);
    if (this.read(address) === null) {
      this.objects.set(address, data);
    }
    return address;
  }

  private read(address: string): Buffer | null {
    const data = this.objects.get(address);
    return data !== undefined && addressOf(data) === address ? data : null;
  }

  // Level 1
  put(data: string): string {
    return this.write(Buffer.from(data, "utf8"));
  }

  get(address: string): string {
    const data = this.read(address);
    return data === null ? "" : data.toString("utf8");
  }

  check(address: string): string {
    if (!this.objects.has(address)) {
      return "missing";
    }
    return this.read(address) === null ? "damaged" : "ok";
  }

  damage(address: string, data: string): boolean {
    if (!this.objects.has(address)) {
      return false;
    }
    this.objects.set(address, Buffer.from(data, "utf8"));
    return true;
  }

  count(): number {
    return this.objects.size;
  }

  bytesStored(): number {
    let total = 0;
    for (const data of this.objects.values()) {
      total += data.length;
    }
    return total;
  }

  // Level 2
  snapshot(files: string[][]): string {
    return this.folder(files.map(([path, data]) => [path.split("/"), data] as [string[], string]));
  }

  private folder(files: [string[], string][]): string {
    const entries = new Map<string, Entry>();
    const below = new Map<string, [string[], string][]>();
    for (const [names, data] of files) {
      if (names.length === 1) {
        entries.set(names[0], { kind: "blob", address: this.put(data) });
      } else {
        const inner = below.get(names[0]) ?? [];
        inner.push([names.slice(1), data]);
        below.set(names[0], inner);
      }
    }
    for (const [name, inner] of below) {
      entries.set(name, { kind: "tree", address: this.folder(inner) });
    }
    // Names are ASCII, so the default sort, by UTF-16 code units, sorts by character code.
    const text = [...entries.keys()]
      .sort()
      .map((name) => `${entries.get(name)!.kind} ${entries.get(name)!.address} ${name}\n`)
      .join("");
    return this.put(text);
  }

  private openTree(address: string): Map<string, Entry> {
    const data = this.read(address);
    if (data === null) {
      throw new Damaged(address);
    }
    const entries = new Map<string, Entry>();
    for (const line of lines(data.toString("utf8"))) {
      const kind = line.slice(0, 4);
      entries.set(line.slice(70), { kind, address: line.slice(5, 69) });
    }
    return entries;
  }

  readPath(root: string, path: string): string {
    let entry: Entry = { kind: "tree", address: root };
    try {
      for (const name of path.split("/")) {
        if (entry.kind !== "tree") {
          return "";
        }
        const found = this.openTree(entry.address).get(name);
        if (found === undefined) {
          return "";
        }
        entry = found;
      }
    } catch (error) {
      if (error instanceof Damaged) {
        return "";
      }
      throw error;
    }
    return entry.kind === "blob" ? this.get(entry.address) : "";
  }

  diff(oldRoot: string, newRoot: string): string[] {
    const changes: [string, string][] = [];
    try {
      this.compare("", oldRoot, newRoot, changes);
    } catch (error) {
      if (error instanceof Damaged) {
        return [];
      }
      throw error;
    }
    changes.sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
    return changes.map(([path, op]) => `${op} ${path}`);
  }

  private compare(prefix: string, oldTree: string, newTree: string, changes: [string, string][]) {
    if (oldTree === newTree) {
      return;
    }
    const before = this.openTree(oldTree);
    const after = this.openTree(newTree);
    for (const name of new Set([...before.keys(), ...after.keys()])) {
      const path = prefix + name;
      const was = before.get(name);
      const now = after.get(name);
      if (was && now && was.kind === now.kind && was.address === now.address) {
        continue;
      }
      if (was && now && was.kind === "blob" && now.kind === "blob") {
        changes.push([path, "M"]);
      } else if (was && now && was.kind === "tree" && now.kind === "tree") {
        this.compare(`${path}/`, was.address, now.address, changes);
      } else {
        if (was) {
          this.listFiles("D", path, was, changes);
        }
        if (now) {
          this.listFiles("A", path, now, changes);
        }
      }
    }
  }

  private listFiles(op: string, path: string, entry: Entry, changes: [string, string][]) {
    if (entry.kind === "blob") {
      changes.push([path, op]);
      return;
    }
    for (const [name, inner] of this.openTree(entry.address)) {
      this.listFiles(op, `${path}/${name}`, inner, changes);
    }
  }

  // Level 3
  chunkSizes(data: string, method: string): number[] {
    const raw = Buffer.from(data, "utf8");
    return method === "fixed" ? fixedSizes(raw.length) : cdcSizes(raw);
  }

  putFile(data: string, method: string): string {
    const raw = Buffer.from(data, "utf8");
    const seen = this.chunks.get(method)!;
    let manifest = "";
    let start = 0;
    for (const size of this.chunkSizes(data, method)) {
      const address = this.write(raw.subarray(start, start + size));
      seen.set(address, size);
      manifest += `${address}\n`;
      start += size;
    }
    this.fileBytes.set(method, this.fileBytes.get(method)! + raw.length);
    return this.put(manifest);
  }

  readFile(manifest: string): string {
    const listing = this.read(manifest);
    if (listing === null) {
      return "";
    }
    const parts: Buffer[] = [];
    for (const address of lines(listing.toString("utf8"))) {
      const chunk = this.read(address);
      if (chunk === null) {
        return "";
      }
      parts.push(chunk);
    }
    return Buffer.concat(parts).toString("utf8");
  }

  dedupRatio(method: string): number {
    let stored = 0;
    for (const size of this.chunks.get(method)!.values()) {
      stored += size;
    }
    return stored === 0 ? 0 : this.fileBytes.get(method)! / stored;
  }

  // Level 4
  setRef(name: string, kind: string, address: string): boolean {
    if (!KINDS.has(kind) || !this.objects.has(address)) {
      return false;
    }
    this.refs.set(name, { kind, address });
    return true;
  }

  getRef(name: string): string {
    return this.refs.get(name)?.address ?? "";
  }

  deleteRef(name: string): boolean {
    return this.refs.delete(name);
  }

  collectGarbage(): number {
    let live: Set<string>;
    try {
      live = this.mark();
    } catch (error) {
      if (error instanceof Damaged) {
        return -1;
      }
      throw error;
    }
    let freed = 0;
    for (const [address, data] of this.objects) {
      if (!live.has(address)) {
        freed += data.length;
        this.objects.delete(address);
      }
    }
    return freed;
  }

  private mark(): Set<string> {
    const live = new Set<string>();
    const visited = new Set<string>();
    const pending: Entry[] = [...this.refs.values()];
    while (pending.length > 0) {
      const entry = pending.pop()!;
      const key = `${entry.kind} ${entry.address}`;
      if (visited.has(key)) {
        continue;
      }
      visited.add(key);
      live.add(entry.address);
      if (entry.kind === "tree") {
        pending.push(...this.openTree(entry.address).values());
      } else if (entry.kind === "manifest") {
        const listing = this.read(entry.address);
        if (listing === null) {
          throw new Damaged(entry.address);
        }
        for (const address of lines(listing.toString("utf8"))) {
          pending.push({ kind: "blob", address });
        }
      }
    }
    return live;
  }
}

import { createHash } from "node:crypto";

const GENESIS = Buffer.alloc(32);
const LEAF_PREFIX = Buffer.from([0x00]);
const NODE_PREFIX = Buffer.from([0x01]);
const HEX_DIGEST = /^[0-9a-f]{64}$/;

function sha256(...parts: Buffer[]): Buffer {
  const hash = createHash("sha256");
  for (const part of parts) {
    hash.update(part);
  }
  return hash.digest();
}

// A field is its length in bytes (4 bytes, big-endian) and then its UTF-8 bytes.
function encodeText(value: string): Buffer {
  const data = Buffer.from(value, "utf8");
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  return Buffer.concat([length, data]);
}

// Drops trailing fractional zeros and a dangling point, and writes `-0` as `0`.
function canonicalAmount(amount: string): string {
  const trimmed = amount.includes(".") ? amount.replace(/0+$/, "").replace(/\.$/, "") : amount;
  return trimmed === "-0" ? "0" : trimmed;
}

function recordDigest(record: string[]): Buffer {
  const [id, sender, receiver, amount] = record;
  return sha256(
    encodeText(id),
    encodeText(sender),
    encodeText(receiver),
    encodeText(canonicalAmount(amount)),
  );
}

function leafDigest(digestOfRecord: Buffer): Buffer {
  return sha256(LEAF_PREFIX, digestOfRecord);
}

function nodeDigest(left: Buffer, right: Buffer): Buffer {
  return sha256(NODE_PREFIX, left, right);
}

// Everything a batch can be asked is computed once, when it is built.
class Batch {
  readonly recordDigests: Buffer[];
  readonly digest: Buffer;
  private tree: Buffer[][] | null = null;

  constructor(records: string[][]) {
    this.recordDigests = records.map(recordDigest);
    this.digest = sha256(...this.recordDigests);
  }

  // The Merkle tree from the leaves up; a level of odd length is padded when it is paired.
  levels(): Buffer[][] {
    if (this.tree === null) {
      let level = this.recordDigests.map(leafDigest);
      const tree = [level];
      while (level.length > 1) {
        const padded = level.length % 2 === 1 ? [...level, level[level.length - 1]] : level;
        const next: Buffer[] = [];
        for (let i = 0; i < padded.length; i += 2) {
          next.push(nodeDigest(padded[i], padded[i + 1]));
        }
        level = next;
        tree.push(level);
      }
      this.tree = tree;
    }
    return this.tree;
  }

  root(): Buffer {
    const tree = this.levels();
    return tree[tree.length - 1][0];
  }

  proof(recordIndex: number): string[][] {
    const steps: string[][] = [];
    let index = recordIndex;
    for (const level of this.levels().slice(0, -1)) {
      const padded = level.length % 2 === 1 ? [...level, level[level.length - 1]] : level;
      const sibling = index ^ 1;
      steps.push([sibling < index ? "L" : "R", padded[sibling].toString("hex")]);
      index = Math.floor(index / 2);
    }
    return steps;
  }
}

class Chain {
  private pending: string[][] = [];
  readonly batches: Batch[] = [];
  readonly digests: Buffer[] = [];

  private readonly batchSize: number;

  constructor(batchSize: number) {
    this.batchSize = batchSize;
  }

  add(record: string[]): void {
    this.pending.push(record);
    if (this.pending.length === this.batchSize) {
      const batch = new Batch(this.pending);
      this.pending = [];
      this.batches.push(batch);
      this.digests.push(sha256(this.tip(), batch.digest));
    }
  }

  tip(): Buffer {
    return this.digests.length > 0 ? this.digests[this.digests.length - 1] : GENESIS;
  }
}

export class Ledger {
  private readonly batches = new Map<string, Batch>();
  private readonly chains = new Map<string, Chain>();

  // Level 1
  addBatch(name: string, records: string[][]): void {
    this.batches.set(name, new Batch(records));
  }

  batchDigest(name: string): string {
    return this.batches.get(name)!.digest.toString("hex");
  }

  sameBatch(first: string, second: string): boolean {
    return this.batches.get(first)!.digest.equals(this.batches.get(second)!.digest);
  }

  // Level 2
  newChain(name: string, batchSize: number): void {
    this.chains.set(name, new Chain(batchSize));
  }

  addRecord(name: string, record: string[]): void {
    this.chains.get(name)!.add(record);
  }

  sealedCount(name: string): number {
    return this.chains.get(name)!.batches.length;
  }

  chainDigest(name: string): string {
    return this.chains.get(name)!.tip().toString("hex");
  }

  sameChain(first: string, second: string): boolean {
    return this.chains.get(first)!.tip().equals(this.chains.get(second)!.tip());
  }

  // Level 3
  // The prefix digests agree up to some length and never again, so the length can be bisected.
  commonPrefix(first: string, second: string): number {
    const left = this.chains.get(first)!.digests;
    const right = this.chains.get(second)!.digests;
    let low = 0;
    let high = Math.min(left.length, right.length);
    while (low < high) {
      const middle = Math.floor((low + high + 1) / 2);
      if (left[middle - 1].equals(right[middle - 1])) {
        low = middle;
      } else {
        high = middle - 1;
      }
    }
    return low;
  }

  // Level 4
  merkleRoot(name: string, batchIndex: number): string {
    return this.chains.get(name)!.batches[batchIndex].root().toString("hex");
  }

  proof(name: string, batchIndex: number, recordIndex: number): string[][] {
    return this.chains.get(name)!.batches[batchIndex].proof(recordIndex);
  }

  verify(root: string, record: string[], proof: string[][]): boolean {
    let current = leafDigest(recordDigest(record));
    for (const step of proof) {
      if (step.length !== 2 || (step[0] !== "L" && step[0] !== "R") || !HEX_DIGEST.test(step[1])) {
        return false;
      }
      const sibling = Buffer.from(step[1], "hex");
      current = step[0] === "L" ? nodeDigest(sibling, current) : nodeDigest(current, sibling);
    }
    return current.toString("hex") === root;
  }
}

import { createHash } from "node:crypto";

const RECEIPT_LENGTH = 12;
const TRUSTED = "trusted";
const STALE = "stale";
const UNSUPPORTED = "unsupported";
const CONTRADICTED = "contradicted";
const STATUSES = [TRUSTED, STALE, UNSUPPORTED, CONTRADICTED];
const USABLE = new Map<string, Set<string>>([
  ["strict", new Set([TRUSTED])],
  ["lenient", new Set([TRUSTED, STALE])],
]);

/** The first 12 hexadecimal characters of the SHA-256 digest of the text's UTF-8 bytes. */
function receipt(text: string): string {
  return createHash("sha256").update(text, "utf8").digest("hex").slice(0, RECEIPT_LENGTH);
}

function rank(status: string): number {
  return STATUSES.indexOf(status);
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

/** Claim texts and queries are printable ASCII, so toLowerCase only changes A to Z. */
function words(text: string): Set<string> {
  return new Set(text.toLowerCase().match(/[a-z0-9]+/g) ?? []);
}

/**
 * A source's current text, the receipts of its versions, and the last position of each receipt
 * in that history, whose keys are the receipts of every text it has held.
 */
class Source {
  text = "";
  readonly history: string[] = [];
  readonly last = new Map<string, number>();

  constructor(text: string) {
    this.append(text);
  }

  append(text: string): void {
    this.text = text;
    this.last.set(receipt(text), this.history.length);
    this.history.push(receipt(text));
  }

  current(): string {
    return this.history[this.history.length - 1];
  }

  /** Versions since the cited receipt was last the current one. */
  behind(cited: string): number {
    return this.history.length - 1 - (this.last.get(cited) ?? 0);
  }
}

class Citation {
  receipt: string;
  refuted = false;

  constructor(cited: string) {
    this.receipt = cited;
  }
}

class Claim {
  readonly order: number;
  readonly text: string;
  readonly citations: Map<string, Citation>;
  readonly premises: string[];
  status = TRUSTED;

  constructor(order: number, text: string, citations: Map<string, Citation>, premises: string[]) {
    this.order = order;
    this.text = text;
    this.citations = citations;
    this.premises = premises;
  }
}

export class GroundedMemory {
  private readonly sources = new Map<string, Source>();
  private readonly claims = new Map<string, Claim>();
  private readonly citingIds = new Map<string, string[]>();
  private readonly resting = new Map<string, string[]>();

  // Level 1
  addSource(sourceId: string, text: string): string {
    if (this.sources.has(sourceId)) {
      return "";
    }
    const source = new Source(text);
    this.sources.set(sourceId, source);
    this.citingIds.set(sourceId, []);
    return source.current();
  }

  addClaim(claimId: string, text: string, citations: string[][]): boolean {
    if (this.claims.has(claimId) || citations.length === 0) {
      return false;
    }
    const cited = new Map<string, Citation>();
    for (const [sourceId, given] of citations) {
      const source = this.sources.get(sourceId);
      if (source === undefined || cited.has(sourceId) || !source.last.has(given)) {
        return false;
      }
      cited.set(sourceId, new Citation(given));
    }
    const claim = new Claim(this.claims.size, text, cited, []);
    this.claims.set(claimId, claim);
    this.resting.set(claimId, []);
    for (const sourceId of cited.keys()) {
      this.citingIds.get(sourceId)!.push(claimId);
    }
    claim.status = this.statusOf(claim);
    return true;
  }

  status(claimId: string): string {
    return this.claims.get(claimId)?.status ?? "";
  }

  evidence(claimId: string): string[][] {
    const claim = this.claims.get(claimId);
    if (claim === undefined) {
      return [];
    }
    return [...claim.citations.keys()]
      .sort(compareText)
      .map((sourceId) => [sourceId, claim.citations.get(sourceId)!.receipt]);
  }

  citing(sourceId: string): string[] {
    return [...(this.citingIds.get(sourceId) ?? [])].sort(compareText);
  }

  // Level 2
  updateSource(sourceId: string, text: string): string[][] {
    const source = this.sources.get(sourceId);
    if (source === undefined || receipt(text) === source.current()) {
      return [];
    }
    source.append(text);
    return this.refresh(this.citingIds.get(sourceId)!);
  }

  history(sourceId: string): string[] {
    return [...(this.sources.get(sourceId)?.history ?? [])];
  }

  drift(claimId: string): string[][] {
    const claim = this.claims.get(claimId);
    if (claim === undefined) {
      return [];
    }
    const rows: string[][] = [];
    for (const sourceId of [...claim.citations.keys()].sort(compareText)) {
      const cited = claim.citations.get(sourceId)!.receipt;
      const source = this.sources.get(sourceId)!;
      if (cited !== source.current()) {
        rows.push([sourceId, cited, source.current(), String(source.behind(cited))]);
      }
    }
    return rows;
  }

  staleClaims(): string[] {
    const ids: string[] = [];
    for (const [claimId, claim] of this.claims) {
      if (claim.status === STALE) {
        ids.push(claimId);
      }
    }
    return ids.sort(compareText);
  }

  // Level 3
  addDerived(claimId: string, text: string, premises: string[]): boolean {
    if (this.claims.has(claimId) || premises.length === 0) {
      return false;
    }
    if (new Set(premises).size !== premises.length || premises.some((p) => !this.claims.has(p))) {
      return false;
    }
    const claim = new Claim(this.claims.size, text, new Map(), [...premises]);
    this.claims.set(claimId, claim);
    this.resting.set(claimId, []);
    for (const premise of premises) {
      this.resting.get(premise)!.push(claimId);
    }
    claim.status = this.statusOf(claim);
    return true;
  }

  verify(claimId: string, sourceId: string, phrase: string): string[][] {
    const citation = this.claims.get(claimId)?.citations.get(sourceId);
    if (citation === undefined) {
      return [];
    }
    const source = this.sources.get(sourceId)!;
    if (source.text.includes(phrase)) {
      citation.receipt = source.current();
      citation.refuted = false;
    } else {
      citation.refuted = true;
    }
    return this.refresh([claimId]);
  }

  dependents(claimId: string): string[] {
    if (!this.claims.has(claimId)) {
      return [];
    }
    const reached = this.downstream([claimId]);
    reached.delete(claimId);
    return [...reached].sort(compareText);
  }

  // Level 4
  recall(query: string, policy: string, k: number): string[][] {
    const wanted = words(query);
    const usable = USABLE.get(policy) ?? new Set<string>();
    const found: string[] = [];
    for (const [claimId, claim] of this.claims) {
      if (!usable.has(claim.status)) {
        continue;
      }
      const have = words(claim.text);
      if ([...wanted].every((word) => have.has(word))) {
        found.push(claimId);
      }
    }
    const status = (claimId: string): number => rank(this.claims.get(claimId)!.status);
    found.sort((a, b) => status(a) - status(b) || compareText(a, b));
    return found.slice(0, k).map((claimId) => this.row(claimId));
  }

  report(): string[] {
    const counts = new Map<string, number>(STATUSES.map((status) => [status, 0]));
    for (const claim of this.claims.values()) {
      counts.set(claim.status, counts.get(claim.status)! + 1);
    }
    const total = this.claims.size;
    const drifted = new Set<string>();
    let mostBehind = 0;
    for (const claim of this.claims.values()) {
      for (const [sourceId, citation] of claim.citations) {
        const source = this.sources.get(sourceId)!;
        if (citation.receipt !== source.current()) {
          drifted.add(sourceId);
          mostBehind = Math.max(mostBehind, source.behind(citation.receipt));
        }
      }
    }
    const trusted = counts.get(TRUSTED)!;
    const share = total === 0 ? "n/a" : `${Math.floor((trusted * 100) / total)}%`;
    return [
      `claims: ${total}`,
      ...STATUSES.map((status) => `${status}: ${counts.get(status)}`),
      `supported: ${share}`,
      `sources: ${this.sources.size}`,
      `drifted sources: ${drifted.size}`,
      `max behind: ${mostBehind}`,
    ];
  }

  // Status upkeep
  private statusOf(claim: Claim): string {
    if (claim.citations.size > 0) {
      let worst = TRUSTED;
      for (const [sourceId, citation] of claim.citations) {
        if (citation.refuted) {
          return CONTRADICTED;
        }
        if (citation.receipt !== this.sources.get(sourceId)!.current()) {
          worst = STALE;
        }
      }
      return worst;
    }
    let worst = TRUSTED;
    for (const premise of claim.premises) {
      let inherited = this.claims.get(premise)!.status;
      if (inherited === CONTRADICTED) {
        inherited = UNSUPPORTED;
      }
      if (rank(inherited) > rank(worst)) {
        worst = inherited;
      }
    }
    return worst;
  }

  private downstream(seeds: string[]): Set<string> {
    const reached = new Set(seeds);
    const stack = [...seeds];
    while (stack.length > 0) {
      for (const dependent of this.resting.get(stack.pop()!)!) {
        if (!reached.has(dependent)) {
          reached.add(dependent);
          stack.push(dependent);
        }
      }
    }
    return reached;
  }

  /**
   * Recomputes the seeds and everything resting on them, premises first: a claim only rests on
   * claims added before it, so the order of addition is a topological order.
   */
  private refresh(seeds: string[]): string[][] {
    const order = (claimId: string): number => this.claims.get(claimId)!.order;
    const affected = [...this.downstream(seeds)].sort((a, b) => order(a) - order(b));
    const changes: string[][] = [];
    for (const claimId of affected) {
      const claim = this.claims.get(claimId)!;
      const before = claim.status;
      claim.status = this.statusOf(claim);
      if (claim.status !== before) {
        changes.push([claimId, before, claim.status]);
      }
    }
    return changes.sort((a, b) => compareText(a[0], b[0]));
  }

  private row(claimId: string): string[] {
    const claim = this.claims.get(claimId)!;
    const row = [claimId, claim.status, claim.text];
    for (const sourceId of [...claim.citations.keys()].sort(compareText)) {
      const cited = claim.citations.get(sourceId)!.receipt;
      const outdated = cited !== this.sources.get(sourceId)!.current();
      row.push(`${sourceId}@${cited}${outdated ? " (outdated)" : ""}`);
    }
    for (const premise of [...claim.premises].sort(compareText)) {
      const stale = this.claims.get(premise)!.status === STALE;
      row.push(`${premise}${stale ? " (stale)" : ""}`);
    }
    return row;
  }
}

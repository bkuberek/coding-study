// Servers answer from their own records the way an authoritative server does: an answer, a
// referral to a delegated child zone, or a negative answer with the zone's SOA. The resolver
// walks from the closest zone whose servers it knows (the root at first) down the referrals, and
// keeps three caches: answers, which it may return; referral data (NS sets and glue), which it
// only uses to find servers; and negative answers. Every entry expires on the virtual clock.
const ROOT = ".";
const MAX_CHAIN = 8;
const NAME_DATA = new Set(["CNAME", "NS", "MX", "SOA"]);
const NXDOMAIN_KEY = "*";
const SEP = " ";

type Rows = string[][];

interface RecordSet {
  ttl: number;
  values: string[];
}

interface Entry {
  expiry: number;
  values: string[];
}

/** What asking one address led to: a final response, a zone to descend to, or nothing. */
type Step = { response: Rows } | { child: string } | null;

function key(name: string, type: string): string {
  return name + SEP + type;
}

function ancestors(name: string): string[] {
  if (name === ROOT) return [ROOT];
  const labels = name.split(".");
  return [...labels.map((_, i) => labels.slice(i).join(".")), ROOT];
}

function within(name: string, zone: string): boolean {
  return zone === ROOT || name === zone || name.endsWith("." + zone);
}

function soaMinimum(data: string): number {
  return Number(data.split(" ")[6]);
}

function compareStrings(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export class DnsResolver {
  private servers = new Map<string, Map<string, RecordSet>>();
  private hints = new Map<string, string[]>();
  private answers = new Map<string, Entry>();
  private referrals = new Map<string, Entry>();
  private glue = new Map<string, Entry>();
  private negative = new Map<string, number>();
  private queries: Rows = [];
  private now = 0;

  // Level 1
  addRecord(server: string, name: string, rtype: string, ttl: number, data: string): void {
    let records = this.servers.get(server);
    if (records === undefined) {
      records = new Map();
      this.servers.set(server, records);
    }
    const value = NAME_DATA.has(rtype) ? data.toLowerCase() : data;
    const k = key(name.toLowerCase(), rtype);
    const values = records.get(k)?.values ?? [];
    if (!values.includes(value)) values.push(value);
    values.sort(compareStrings);
    records.set(k, { ttl, values });
  }

  lookup(server: string, name: string, qtype: string): string[][] {
    const records = this.servers.get(server) ?? new Map<string, RecordSet>();
    name = name.toLowerCase();
    let zone: string | null = null;
    for (const k of records.keys()) {
      const [owner, type] = k.split(SEP);
      if (type === "SOA" && within(name, owner)) {
        if (zone === null || ancestors(owner).length > ancestors(zone).length) zone = owner;
      }
    }
    if (zone === null) return [["REFUSED"]];
    for (const node of ancestors(name).reverse()) {
      if (node !== zone && within(node, zone) && records.has(key(node, "NS"))) {
        return DnsResolver.referral(records, node);
      }
    }
    if (records.has(key(name, qtype))) {
      return [["NOERROR"], ...DnsResolver.section(records, "answer", name, qtype)];
    }
    if (qtype !== "CNAME" && records.has(key(name, "CNAME"))) {
      return [["NOERROR"], ...DnsResolver.section(records, "answer", name, "CNAME")];
    }
    const soa = records.get(key(zone, "SOA"))!;
    const ttl = Math.min(soa.ttl, soaMinimum(soa.values[0]));
    const authority = ["authority", zone, "SOA", String(ttl), soa.values[0]];
    const exists = [...records.keys()].some((k) => within(k.split(SEP)[0], name));
    return [[exists ? "NOERROR" : "NXDOMAIN"], authority];
  }

  // Level 2
  follow(server: string, name: string, qtype: string): string[][] {
    let current = name.toLowerCase();
    const visited = new Set([current]);
    const chain: Rows = [];
    for (;;) {
      const response = this.lookup(server, current, qtype);
      if (response[0][0] === "REFUSED") return chain.length > 0 ? [["NOERROR"], ...chain] : response;
      const alias = DnsResolver.alias(response, qtype);
      if (alias === null) return [response[0], ...chain, ...response.slice(1)];
      chain.push(alias);
      current = alias[4];
      if (visited.has(current) || chain.length > MAX_CHAIN) return [["SERVFAIL"], ...chain];
      visited.add(current);
    }
  }

  // Level 3
  addRootHint(name: string, address: string): void {
    const lower = name.toLowerCase();
    const addresses = this.hints.get(lower) ?? [];
    if (!addresses.includes(address)) addresses.push(address);
    addresses.sort(compareStrings);
    this.hints.set(lower, addresses);
  }

  resolve(name: string, qtype: string, now: number): string[][] {
    this.now = now;
    this.queries = [];
    const [code, rows] = this.resolveName(name.toLowerCase(), qtype, new Set());
    return [[code], ...rows];
  }

  trace(): string[][] {
    return this.queries.map((query) => [...query]);
  }

  // Level 4
  negatives(now: number): string[][] {
    const rows: Rows = [];
    for (const [k, expiry] of this.negative) {
      if (now < expiry) rows.push([...k.split(SEP), String(expiry - now)]);
    }
    return rows.sort((a, b) => compareStrings(a[0], b[0]) || compareStrings(a[1], b[1]));
  }

  // Server side
  private static section(records: Map<string, RecordSet>, section: string, owner: string, type: string): Rows {
    const set = records.get(key(owner, type))!;
    return set.values.map((value) => [section, owner, type, String(set.ttl), value]);
  }

  private static referral(records: Map<string, RecordSet>, cut: string): Rows {
    const authority = DnsResolver.section(records, "authority", cut, "NS");
    const additional: Rows = [];
    for (const target of records.get(key(cut, "NS"))!.values) {
      for (const type of ["A", "AAAA"]) {
        if (records.has(key(target, type))) {
          additional.push(...DnsResolver.section(records, "additional", target, type));
        }
      }
    }
    additional.sort(
      (a, b) => compareStrings(a[1], b[1]) || compareStrings(a[2], b[2]) || compareStrings(a[4], b[4]),
    );
    return [["NOERROR"], ...authority, ...additional];
  }

  private static alias(response: Rows, qtype: string): string[] | null {
    const answers = response.slice(1).filter((row) => row[0] === "answer");
    if (qtype !== "CNAME" && answers.length === 1 && answers[0][2] === "CNAME") return answers[0];
    return null;
  }

  // Resolver side
  private valid(entry: Entry | undefined): string[] | null {
    return entry !== undefined && this.now < entry.expiry ? entry.values : null;
  }

  private cached(name: string, type: string): Rows | null {
    const entry = this.answers.get(key(name, type));
    if (entry === undefined || this.now >= entry.expiry) return null;
    return entry.values.map((value) => ["answer", name, type, String(entry.expiry - this.now), value]);
  }

  private resolveName(qname: string, qtype: string, pending: Set<string>): [string, Rows] {
    const chain: Rows = [];
    const visited = new Set([qname]);
    let current = qname;
    for (;;) {
      const found = this.cached(current, qtype);
      if (found !== null) return ["NOERROR", [...chain, ...found]];
      let alias = qtype !== "CNAME" ? this.cached(current, "CNAME")?.[0] ?? null : null;
      if (alias === null) {
        const negative = this.negativeAnswer(current, qtype);
        if (negative !== null) return [negative, chain];
        const response = this.ask(current, qtype, pending);
        if (response === null) return ["SERVFAIL", chain];
        alias = this.absorb(response, current, qtype);
        if (alias === null) {
          const rows = response.slice(1).filter((row) => row[0] === "answer");
          return [response[0][0], [...chain, ...rows]];
        }
      }
      chain.push(alias);
      current = alias[4];
      if (visited.has(current) || chain.length > MAX_CHAIN) return ["SERVFAIL", chain];
      visited.add(current);
    }
  }

  /** Caches a final response and returns its CNAME when it is an alias. */
  private absorb(response: Rows, qname: string, qtype: string): string[] | null {
    const answers = response.slice(1).filter((row) => row[0] === "answer");
    if (answers.length > 0) {
      this.answers.set(key(qname, answers[0][2]), {
        expiry: this.now + Number(answers[0][3]),
        values: answers.map((row) => row[4]),
      });
      return DnsResolver.alias(response, qtype);
    }
    const soa = response.slice(1).find((row) => row[2] === "SOA");
    if (soa !== undefined) {
      const type = response[0][0] === "NXDOMAIN" ? NXDOMAIN_KEY : qtype;
      this.negative.set(key(qname, type), this.now + Number(soa[3]));
    }
    return null;
  }

  private negativeAnswer(name: string, qtype: string): string | null {
    if (this.now < (this.negative.get(key(name, NXDOMAIN_KEY)) ?? this.now)) return "NXDOMAIN";
    if (this.now < (this.negative.get(key(name, qtype)) ?? this.now)) return "NOERROR";
    return null;
  }

  private nsNames(zone: string): string[] | null {
    if (zone === ROOT) return this.hints.size > 0 ? [...this.hints.keys()].sort(compareStrings) : null;
    return this.valid(this.answers.get(key(zone, "NS"))) ?? this.valid(this.referrals.get(zone));
  }

  private knownAddresses(zone: string, server: string): string[] {
    if (zone === ROOT) return this.hints.get(server) ?? [];
    for (const source of [this.answers, this.glue]) {
      const found = ["A", "AAAA"].flatMap((type) => this.valid(source.get(key(server, type))) ?? []);
      if (found.length > 0) return found;
    }
    return [];
  }

  /** Walks down from the closest zone with known servers to a final response. */
  private ask(qname: string, qtype: string, pending: Set<string>): Rows | null {
    let zone = ancestors(qname).find((z) => z === ROOT || this.nsNames(z) !== null)!;
    for (;;) {
      const step = this.askZone(zone, qname, qtype, pending);
      if (step === null) return null;
      if ("response" in step) return step.response;
      zone = step.child;
    }
  }

  /** Asks the servers of one zone: those whose addresses are known first, then the others,
   * each looked up first; an address is asked once per zone. */
  private askZone(zone: string, qname: string, qtype: string, pending: Set<string>): Step {
    const names = this.nsNames(zone) ?? [];
    const seen = new Set<string>();
    const known = names.map((server) => [server, this.knownAddresses(zone, server)] as const);
    const tryAll = (addresses: readonly string[]): Step => {
      for (const address of addresses) {
        if (seen.has(address)) continue;
        seen.add(address);
        const step = this.askAddress(address, zone, qname, qtype);
        if (step !== null) return step;
      }
      return null;
    };
    for (const [, addresses] of known) {
      const step = tryAll(addresses);
      if (step !== null) return step;
    }
    for (const [server, first] of known) {
      if (first.length > 0) continue;
      let addresses = this.knownAddresses(zone, server);
      if (addresses.length === 0 && !pending.has(server)) {
        const [, rows] = this.resolveName(server, "A", new Set([...pending, server]));
        addresses = rows.filter((row) => row[2] === "A").map((row) => row[4]);
      }
      const step = tryAll(addresses);
      if (step !== null) return step;
    }
    return null;
  }

  private askAddress(address: string, zone: string, qname: string, qtype: string): Step {
    this.queries.push([address, qname, qtype]);
    const response = this.lookup(address, qname, qtype);
    if (response[0][0] === "REFUSED") return null;
    const cut = DnsResolver.referralZone(response);
    if (cut === null) return { response };
    if (cut !== zone && within(cut, zone) && within(qname, cut)) {
      this.rememberReferral(response, zone);
      return { child: cut };
    }
    return null;
  }

  private static referralZone(response: Rows): string | null {
    if (response.slice(1).some((row) => row[0] === "answer")) return null;
    const ns = response.slice(1).find((row) => row[0] === "authority" && row[2] === "NS");
    return ns === undefined ? null : ns[1];
  }

  private rememberReferral(response: Rows, zone: string): void {
    const ns = response.slice(1).filter((row) => row[0] === "authority");
    this.referrals.set(ns[0][1], { expiry: this.now + Number(ns[0][3]), values: ns.map((row) => row[4]) });
    const groups = new Map<string, Rows>();
    for (const row of response.slice(1)) {
      if (row[0] === "additional" && within(row[1], zone)) {
        const k = key(row[1], row[2]);
        groups.set(k, [...(groups.get(k) ?? []), row]);
      }
    }
    for (const [k, rows] of groups) {
      this.glue.set(k, { expiry: this.now + Number(rows[0][3]), values: rows.map((row) => row[4]) });
    }
  }
}

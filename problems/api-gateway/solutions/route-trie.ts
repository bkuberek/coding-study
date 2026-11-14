const NOT_FOUND = "404";
const TOO_MANY_REQUESTS = "429";
const UNAVAILABLE = "503";

type BreakerState = "CLOSED" | "OPEN" | "HALF_OPEN";

function segmentsOf(path: string): string[] {
  return path.split("/").filter((segment) => segment.length > 0);
}

// One trie level: literal children, one shared parameter child, and the routes ending here.
class RouteNode {
  readonly literals = new Map<string, RouteNode>();
  parameter: RouteNode | null = null;
  upstream: string | null = null; // a pattern ending exactly here
  wildcard: string | null = null; // a pattern ending here with `*`

  child(segment: string): RouteNode {
    if (segment.startsWith(":")) {
      this.parameter ??= new RouteNode();
      return this.parameter;
    }
    let next = this.literals.get(segment);
    if (next === undefined) {
      next = new RouteNode();
      this.literals.set(segment, next);
    }
    return next;
  }

  // The most specific upstream: literal before parameter before wildcard, left to right.
  match(segments: readonly string[], index: number): string | null {
    if (index === segments.length) {
      return this.upstream;
    }
    const found =
      this.literals.get(segments[index])?.match(segments, index + 1) ??
      this.parameter?.match(segments, index + 1) ??
      null;
    return found ?? this.wildcard;
  }
}

class RouteTable {
  private readonly roots = new Map<string, RouteNode>();

  add(method: string, pattern: string, upstream: string): boolean {
    const [node, wildcard] = this.end(method, pattern);
    if ((wildcard ? node.wildcard : node.upstream) !== null) {
      return false;
    }
    if (wildcard) {
      node.wildcard = upstream;
    } else {
      node.upstream = upstream;
    }
    return true;
  }

  remove(method: string, pattern: string): boolean {
    const [node, wildcard] = this.end(method, pattern);
    const found = wildcard ? node.wildcard : node.upstream;
    if (wildcard) {
      node.wildcard = null;
    } else {
      node.upstream = null;
    }
    return found !== null;
  }

  match(method: string, path: string): string | null {
    return this.roots.get(method)?.match(segmentsOf(path), 0) ?? null;
  }

  // The node where `pattern` ends, and whether it ends with the wildcard.
  private end(method: string, pattern: string): [RouteNode, boolean] {
    const segments = segmentsOf(pattern);
    const wildcard = segments.at(-1) === "*";
    let node = this.roots.get(method);
    if (node === undefined) {
      node = new RouteNode();
      this.roots.set(method, node);
    }
    for (const segment of wildcard ? segments.slice(0, -1) : segments) {
      node = node.child(segment);
    }
    return [node, wildcard];
  }
}

interface RateLimiter {
  allows(now: number): boolean;
  record(now: number): void;
}

class FixedWindow implements RateLimiter {
  private readonly limit: number;
  private readonly window: number;
  private current = -1;
  private used = 0;

  constructor(limit: number, window: number) {
    this.limit = limit;
    this.window = window;
  }

  allows(now: number): boolean {
    return Math.floor(now / this.window) !== this.current || this.used < this.limit;
  }

  record(now: number): void {
    const index = Math.floor(now / this.window);
    if (index !== this.current) {
      this.current = index;
      this.used = 0;
    }
    this.used++;
  }
}

class SlidingWindow implements RateLimiter {
  private readonly limit: number;
  private readonly window: number;
  private readonly accepted: number[] = [];
  private oldest = 0; // index of the oldest accepted request still in the window

  constructor(limit: number, window: number) {
    this.limit = limit;
    this.window = window;
  }

  allows(now: number): boolean {
    while (this.oldest < this.accepted.length && this.accepted[this.oldest] <= now - this.window) {
      this.oldest++;
    }
    return this.accepted.length - this.oldest < this.limit;
  }

  record(now: number): void {
    this.accepted.push(now);
  }
}

class Client {
  limiter: RateLimiter | null = null;
  quota: number | null = null; // requests left, when a quota is set

  allows(now: number): boolean {
    const withinRate = this.limiter === null || this.limiter.allows(now);
    return withinRate && (this.quota === null || this.quota > 0);
  }

  record(now: number): void {
    this.limiter?.record(now);
    if (this.quota !== null) {
      this.quota--;
    }
  }
}

class CircuitBreaker {
  private readonly threshold: number;
  private readonly cooldown: number;
  private failures = 0;
  private openedAt: number | null = null;
  private trialInFlight = false;

  constructor(threshold: number, cooldown: number) {
    this.threshold = threshold;
    this.cooldown = cooldown;
  }

  state(now: number): BreakerState {
    if (this.openedAt === null) {
      return "CLOSED";
    }
    return now >= this.openedAt + this.cooldown ? "HALF_OPEN" : "OPEN";
  }

  allows(now: number): boolean {
    const state = this.state(now);
    return state === "CLOSED" || (state === "HALF_OPEN" && !this.trialInFlight);
  }

  onDispatch(now: number): void {
    if (this.state(now) === "HALF_OPEN") {
      this.trialInFlight = true;
    }
  }

  record(now: number, success: boolean): BreakerState {
    const state = this.state(now);
    if (state === "HALF_OPEN") {
      this.trialInFlight = false;
      this.openedAt = success ? null : now;
    } else if (state === "CLOSED") {
      this.failures = success ? 0 : this.failures + 1;
      if (this.failures >= this.threshold) {
        this.failures = 0;
        this.openedAt = now;
      }
    }
    return this.state(now);
  }
}

export class ApiGateway {
  private readonly routes = new RouteTable();
  private readonly clients = new Map<string, Client>();
  private readonly breakers = new Map<string, CircuitBreaker>();

  // Level 1
  addRoute(timestamp: number, method: string, pattern: string, upstream: string): boolean {
    return this.routes.add(method, pattern, upstream);
  }

  removeRoute(timestamp: number, method: string, pattern: string): boolean {
    return this.routes.remove(method, pattern);
  }

  route(timestamp: number, clientId: string, method: string, path: string): string {
    const upstream = this.routes.match(method, path);
    if (upstream === null) {
      return NOT_FOUND;
    }
    const breaker = this.breakers.get(upstream);
    if (breaker !== undefined && !breaker.allows(timestamp)) {
      return UNAVAILABLE;
    }
    const client = this.clients.get(clientId);
    if (client !== undefined && !client.allows(timestamp)) {
      return TOO_MANY_REQUESTS;
    }
    client?.record(timestamp);
    breaker?.onDispatch(timestamp);
    return upstream;
  }

  // Level 2
  setClientLimit(timestamp: number, clientId: string, limit: number, windowMs: number): void {
    this.client(clientId).limiter = new FixedWindow(limit, windowMs);
  }

  // Level 3
  setClientSlidingLimit(timestamp: number, clientId: string, limit: number, windowMs: number): void {
    this.client(clientId).limiter = new SlidingWindow(limit, windowMs);
  }

  setClientQuota(timestamp: number, clientId: string, quota: number): void {
    this.client(clientId).quota = quota;
  }

  remainingQuota(timestamp: number, clientId: string): number {
    return this.clients.get(clientId)?.quota ?? -1;
  }

  // Level 4
  setBreaker(timestamp: number, upstream: string, failureThreshold: number, cooldownMs: number): void {
    this.breakers.set(upstream, new CircuitBreaker(failureThreshold, cooldownMs));
  }

  reportResult(timestamp: number, upstream: string, success: boolean): string {
    return this.breakers.get(upstream)?.record(timestamp, success) ?? "";
  }

  breakerState(timestamp: number, upstream: string): string {
    return this.breakers.get(upstream)?.state(timestamp) ?? "";
  }

  private client(clientId: string): Client {
    let client = this.clients.get(clientId);
    if (client === undefined) {
      client = new Client();
      this.clients.set(clientId, client);
    }
    return client;
  }
}

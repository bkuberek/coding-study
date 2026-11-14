// The rates vendor, as far as the client can see it: a request goes out, and something comes back,
// or nothing does. A test scripts what each attempt gets.

export interface VendorRequest {
  method: string;
  path: string;
  /** "" when the caller sent none. */
  idempotencyKey: string;
}

export interface VendorAnswer {
  status: number;
  /** The text of the `Retry-After` header, or null when the answer has none. */
  retryAfter: string | null;
}

/** The connection failed before the request reached the vendor. */
export class ConnectionReset extends Error {
  constructor() {
    super("connection reset");
    this.name = "ConnectionReset";
  }
}

const AFTER_THE_SCRIPT = "200 10";
const RETRY_AFTER = "retry-after=";

export class ScriptedVendor {
  readonly #steps: string[] = [];
  readonly #attempts: string[] = [];
  readonly #startedAt = Date.now();

  /** Adds steps to the script, one per attempt: `<status> <latencyMs> [retry-after=<text>]`,
   * `reset <latencyMs>` or `hang`. */
  script(steps: string[]): void {
    this.#steps.push(...steps);
  }

  /** Every attempt the vendor has seen: when it started, what it asked for, and any key. */
  attemptLog(): string[] {
    return [...this.#attempts];
  }

  send(request: VendorRequest): Promise<VendorAnswer> {
    const key = request.idempotencyKey === "" ? "" : ` key=${request.idempotencyKey}`;
    const at = Date.now() - this.#startedAt;
    this.#attempts.push(`${at} ${request.method} ${request.path}${key}`);

    const [kind = "", latency = "0", header] = (this.#steps.shift() ?? AFTER_THE_SCRIPT).split(" ");
    if (kind === "hang") {
      return new Promise(() => {});
    }
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (kind === "reset") {
          reject(new ConnectionReset());
        } else {
          const retryAfter = header?.startsWith(RETRY_AFTER) ? header.slice(RETRY_AFTER.length) : null;
          resolve({ status: Number(kind), retryAfter });
        }
      }, Number(latency));
    });
  }
}

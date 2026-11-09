// The endpoints customers registered, and how each has fared.

import { FAILURES_BEFORE_DISABLING } from "./limits.ts";

export type EndpointView = {
  id: string;
  url: string;
  status: "active" | "disabled";
  consecutive_failures: number;
};

export class Endpoint {
  readonly id: string;
  readonly url: string;
  readonly secret: string;
  #consecutiveFailures = 0;

  constructor(id: string, url: string, secret: string) {
    this.id = id;
    this.url = url;
    this.secret = secret;
  }

  /** Disabled for good once it fails often enough in a row: nothing re-enables it. */
  get disabled(): boolean {
    return this.#consecutiveFailures >= FAILURES_BEFORE_DISABLING;
  }

  recordSuccess(): void {
    this.#consecutiveFailures = 0;
  }

  recordFailure(): void {
    this.#consecutiveFailures += 1;
  }

  view(): EndpointView {
    return {
      id: this.id,
      url: this.url,
      status: this.disabled ? "disabled" : "active",
      consecutive_failures: this.#consecutiveFailures,
    };
  }
}

export class EndpointRegistry {
  readonly #endpoints = new Map<string, Endpoint>();

  has(id: string): boolean {
    return this.#endpoints.has(id);
  }

  get(id: string): Endpoint | undefined {
    return this.#endpoints.get(id);
  }

  /** False when the id is taken, and the registry keeps the endpoint it had. */
  add(endpoint: Endpoint): boolean {
    if (this.#endpoints.has(endpoint.id)) {
      return false;
    }
    this.#endpoints.set(endpoint.id, endpoint);
    return true;
  }
}

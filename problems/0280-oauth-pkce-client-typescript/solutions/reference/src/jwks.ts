// The provider's signing keys, fetched once and kept. A token whose kid the set does not hold makes
// it fetch the set again: that is how a rotated key arrives. Fetches that overlap share one request.

import { createPublicKey } from "node:crypto";
import type { JsonWebKey, KeyObject } from "node:crypto";

type Jwk = JsonWebKey & { kid?: string; use?: string };

/** Where a token's signing key comes from, by its `kid`. */
export type KeySource = { keyFor(kid: string): Promise<KeyObject | undefined> };

const TIMEOUT_MS = 5000;

export class RemoteKeySet implements KeySource {
  readonly #location: () => Promise<string>;
  #keys = new Map<string, KeyObject>();
  #loading: Promise<void> | undefined;

  /** `location` gives the set's URL, the provider's `jwks_uri`. */
  constructor(location: () => Promise<string>) {
    this.#location = location;
  }

  async keyFor(kid: string): Promise<KeyObject | undefined> {
    if (!this.#keys.has(kid)) {
      await this.#reload();
    }
    return this.#keys.get(kid);
  }

  #reload(): Promise<void> {
    this.#loading ??= this.#fetch().finally(() => {
      this.#loading = undefined;
    });
    return this.#loading;
  }

  async #fetch(): Promise<void> {
    const response = await fetch(await this.#location(), { signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!response.ok) {
      throw new Error(`the key set answered ${response.status}`);
    }
    const { keys } = (await response.json()) as { keys: Jwk[] };
    this.#keys = new Map(
      keys
        .filter(isSigningKey)
        .map((jwk) => [jwk.kid as string, createPublicKey({ key: jwk, format: "jwk" })]),
    );
  }
}

function isSigningKey(jwk: Jwk): boolean {
  return jwk.kty === "RSA" && typeof jwk.kid === "string" && (jwk.use ?? "sig") === "sig";
}

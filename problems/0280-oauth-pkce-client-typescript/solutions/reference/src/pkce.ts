// The random values of a login, and the PKCE challenge that binds its code to this app.

import { createHash, randomBytes } from "node:crypto";

/** 32 random bytes as base64url: 43 characters, for a state, a nonce or a code verifier. */
export function randomValue(): string {
  return randomBytes(32).toString("base64url");
}

/** The S256 challenge of a verifier: its SHA-256, as base64url without padding. */
export function challengeOf(verifier: string): string {
  return createHash("sha256").update(verifier).digest("base64url");
}

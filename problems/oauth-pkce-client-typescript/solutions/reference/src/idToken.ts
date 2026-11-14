// An ID token is believed only once the provider's signature over it holds, with RS256 and a key
// from the provider's own set, and then each claim says it was meant for this app, for this login,
// now. The header is the attacker's to write, so it chooses neither the algorithm nor the key.

import { verify } from "node:crypto";

import type { KeySource } from "./jwks.ts";

export const ALGORITHM = "RS256";
export const CLOCK_SKEW_S = 60;

/** Why a token was refused. Its message names the rule and never holds the token. */
export class InvalidToken extends Error {}

export type Expected = { issuer: string; clientId: string; nonce: string; nowSeconds: number };
export type IdClaims = Record<string, unknown> & { sub: string };

export async function verifyIdToken(
  token: string,
  keys: KeySource,
  expected: Expected,
): Promise<IdClaims> {
  const parts = token.split(".");
  if (parts.length !== 3) {
    throw new InvalidToken("not a signed JWT");
  }
  const [encodedHeader, encodedClaims, signature] = parts as [string, string, string];
  const header = decoded(encodedHeader);
  if (header.alg !== ALGORITHM) {
    throw new InvalidToken(`the algorithm is not ${ALGORITHM}`);
  }
  if (typeof header.kid !== "string") {
    throw new InvalidToken("the header names no key");
  }
  const key = await keys.keyFor(header.kid);
  if (key === undefined) {
    throw new InvalidToken("no key of the provider has that kid");
  }
  const signed = Buffer.from(`${encodedHeader}.${encodedClaims}`);
  if (!verify("sha256", signed, key, Buffer.from(signature, "base64url"))) {
    throw new InvalidToken("the signature does not hold");
  }
  const claims = decoded(encodedClaims);
  checkClaims(claims, expected);
  return claims as IdClaims;
}

function checkClaims(claims: Record<string, unknown>, expected: Expected): void {
  const { aud, azp, exp, iat, iss, nonce, sub } = claims;
  if (iss !== expected.issuer) {
    throw new InvalidToken("another issuer");
  }
  const audiences = Array.isArray(aud) ? aud : [aud];
  if (!audiences.includes(expected.clientId)) {
    throw new InvalidToken("meant for another client");
  }
  if (audiences.length > 1 && azp !== expected.clientId) {
    throw new InvalidToken("issued to another client");
  }
  if (typeof exp !== "number" || expected.nowSeconds > exp + CLOCK_SKEW_S) {
    throw new InvalidToken("expired");
  }
  if (typeof iat !== "number" || iat > expected.nowSeconds + CLOCK_SKEW_S) {
    throw new InvalidToken("issued in the future");
  }
  if (nonce !== expected.nonce) {
    throw new InvalidToken("the nonce is not this login's");
  }
  if (typeof sub !== "string" || sub === "") {
    throw new InvalidToken("no subject");
  }
}

function decoded(part: string): Record<string, unknown> {
  let value: unknown;
  try {
    value = JSON.parse(Buffer.from(part, "base64url").toString("utf8"));
  } catch {
    throw new InvalidToken("a part is not base64url JSON");
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new InvalidToken("a part is not a JSON object");
  }
  return value as Record<string, unknown>;
}

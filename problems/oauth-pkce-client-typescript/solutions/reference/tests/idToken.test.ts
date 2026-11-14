// verifyIdToken against tokens signed here with a key of the test's own, so each rule is checked
// without a provider.

import assert from "node:assert/strict";
import { generateKeyPairSync, sign } from "node:crypto";
import type { KeyObject } from "node:crypto";
import { test } from "node:test";

import { InvalidToken, verifyIdToken } from "../src/idToken.ts";
import type { Expected } from "../src/idToken.ts";
import type { KeySource } from "../src/jwks.ts";

const NOW = 1_800_000_000;
const KID = "test-key";
const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const keys: KeySource = { keyFor: async (kid) => (kid === KID ? publicKey : undefined) };
const EXPECTED: Expected = {
  issuer: "http://idp:8080/realms/campus",
  clientId: "portal",
  nonce: "nonce-1",
  nowSeconds: NOW,
};
const CLAIMS = {
  iss: EXPECTED.issuer,
  aud: "portal",
  azp: "portal",
  sub: "user-1",
  nonce: "nonce-1",
  iat: NOW,
  exp: NOW + 300,
};

function encoded(value: unknown): string {
  return Buffer.from(JSON.stringify(value)).toString("base64url");
}

function signed(claims: object, header: object = { alg: "RS256", kid: KID }, key: KeyObject = privateKey): string {
  const body = `${encoded(header)}.${encoded(claims)}`;
  return `${body}.${sign("sha256", Buffer.from(body), key).toString("base64url")}`;
}

async function refused(token: string): Promise<void> {
  await assert.rejects(verifyIdToken(token, keys, EXPECTED), InvalidToken);
}

test("accepts a token the provider signed for this login", async () => {
  const claims = await verifyIdToken(signed(CLAIMS), keys, EXPECTED);

  assert.equal(claims.sub, "user-1");
});

test("refuses a token whose header says alg none", async () => {
  await refused(`${encoded({ alg: "none" })}.${encoded(CLAIMS)}.`);
});

test("refuses a signature by another key under the provider's kid", async () => {
  const other = generateKeyPairSync("rsa", { modulusLength: 2048 }).privateKey;

  await refused(signed(CLAIMS, { alg: "RS256", kid: KID }, other));
});

test("refuses a kid the provider's set does not hold", async () => {
  await refused(signed(CLAIMS, { alg: "RS256", kid: "unknown" }));
});

test("refuses a token meant for another client", async () => {
  await refused(signed({ ...CLAIMS, aud: "another-app" }));
});

test("refuses a token with several audiences issued to another client", async () => {
  await refused(signed({ ...CLAIMS, aud: ["portal", "another-app"], azp: "another-app" }));
});

test("refuses another issuer", async () => {
  await refused(signed({ ...CLAIMS, iss: "http://idp:8080/realms/other" }));
});

test("refuses another login's nonce", async () => {
  await refused(signed({ ...CLAIMS, nonce: "nonce-2" }));
});

test("refuses a token expired beyond the clock skew", async () => {
  await refused(signed({ ...CLAIMS, exp: NOW - 61 }));
});

test("accepts a token expired within the clock skew", async () => {
  const claims = await verifyIdToken(signed({ ...CLAIMS, exp: NOW - 30 }), keys, EXPECTED);

  assert.equal(claims.sub, "user-1");
});

test("refuses a token that is not three parts", async () => {
  await refused("not-a-token");
});

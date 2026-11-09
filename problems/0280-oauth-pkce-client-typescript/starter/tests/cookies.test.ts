// Your tests, run by `cstudy test` inside the sandbox before the visible cases. These cover the
// starter's cookie helpers; add your own beside them, for what you build.

import assert from "node:assert/strict";
import { test } from "node:test";

import { clearedCookie, cookie, readCookies } from "../src/cookies.ts";

test("reads each cookie of a header by name", () => {
  const cookies = readCookies("session=abc; login=def");

  assert.deepEqual([...cookies], [["session", "abc"], ["login", "def"]]);
});

test("reads no cookie from a missing header", () => {
  assert.equal(readCookies(undefined).size, 0);
});

test("keeps a cookie for this app alone", () => {
  assert.equal(cookie("session", "abc", 60), "session=abc; Path=/; HttpOnly; SameSite=Lax; Max-Age=60");
});

test("a cleared cookie expires at once", () => {
  assert.match(clearedCookie("login"), /^login=; .*Max-Age=0$/);
});

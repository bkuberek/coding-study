// Tests of the plumbing and of the field rules.

import assert from "node:assert/strict";
import { test } from "node:test";

import { readJsonObject } from "../src/kernel/body.ts";
import { ApiError } from "../src/kernel/errors.ts";
import { dispatch } from "../src/kernel/router.ts";
import type { Route } from "../src/kernel/router.ts";
import { problemWith, validateAllFields } from "../src/model/supplier.ts";

const ECHO: Route = {
  method: "GET",
  pattern: "/things/:id",
  handle: (request) => ({ status: 200, body: { id: request.params.id } }),
};

test("a route's parameters reach its handler", () => {
  const answer = dispatch([ECHO], { method: "GET", path: "/things/7", body: "" });
  assert.deepEqual(answer.body, { id: "7" });
});

test("an unknown path and a wrong method are different failures", () => {
  const status = (method: string, path: string): number | undefined => {
    try {
      dispatch([ECHO], { method, path, body: "" });
      return undefined;
    } catch (error) {
      return error instanceof ApiError ? error.status : undefined;
    }
  };
  assert.equal(status("GET", "/nope"), 404);
  assert.equal(status("DELETE", "/things/7"), 405);
});

test("a body must be a JSON object", () => {
  assert.throws(() => readJsonObject("[]"), ApiError);
  assert.throws(() => readJsonObject("{broken"), ApiError);
  assert.deepEqual(readJsonObject('{"a":1}'), { a: 1 });
});

test("field rules", () => {
  assert.equal(problemWith("notes", ""), null);
  assert.equal(problemWith("name", "  "), "must be a non-empty string");
  assert.equal(problemWith("minOrderCents", 1.5), "must be a whole number from 0");
  assert.deepEqual(
    validateAllFields({
      name: "n",
      contactEmail: "a@b.example",
      notes: "",
      minOrderCents: 5,
      maxOrderCents: 4,
      status: "active",
    }),
    [{ field: "maxOrderCents", message: "must not be below minOrderCents" }],
  );
});

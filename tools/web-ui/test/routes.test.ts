import assert from "node:assert/strict";
import { test } from "node:test";

import { attemptHash, parseRoute, problemHash, problemsHash } from "../src/page/routes.ts";

test("an empty fragment is the problems view without filters", () => {
  assert.deepEqual(parseRoute(""), { view: "problems", filters: {} });
});

test("the root fragment is the problems view", () => {
  assert.deepEqual(parseRoute("#/"), { view: "problems", filters: {} });
});

test("the problems view keeps its filters in the fragment's query", () => {
  assert.deepEqual(parseRoute("#/?track=dsa&status=due"), {
    view: "problems",
    filters: { track: "dsa", status: "due" },
  });
});

test("the label filters are kept in the fragment's query", () => {
  const filters = { domain: "backend", role: "platform", scope: "function" };
  assert.deepEqual(parseRoute("#/?scope=function&role=platform&domain=backend"), { view: "problems", filters });
  assert.equal(problemsHash(filters), "#/?domain=backend&role=platform&scope=function");
});

test("a query key that is no filter is dropped", () => {
  assert.deepEqual(parseRoute("#/?sort=title&kind=item"), { view: "problems", filters: { kind: "item" } });
});

test("a problem is addressed by its slug", () => {
  assert.deepEqual(parseRoute("#/problems/two-sum"), { view: "problem", slug: "two-sum" });
});

test("an attempt is addressed by its id", () => {
  assert.deepEqual(parseRoute("#/attempts/41"), { view: "attempt", id: 41 });
});

for (const id of ["0", "-1", "4.5", "two"]) {
  test(`an attempt id ${id} names no view`, () => {
    assert.equal(parseRoute(`#/attempts/${id}`).view, "missing");
  });
}

test("health and settings are views of their own", () => {
  assert.deepEqual([parseRoute("#/health").view, parseRoute("#/settings").view], ["health", "settings"]);
});

test("mock and progress are views of their own", () => {
  assert.deepEqual([parseRoute("#/mock").view, parseRoute("#/progress").view], ["mock", "progress"]);
});

test("an unknown fragment is missing", () => {
  assert.deepEqual(parseRoute("#/problems/two-sum/extra"), { view: "missing", fragment: "#/problems/two-sum/extra" });
});

test("filters write back in the order cstudy list takes them, empty ones left out", () => {
  assert.equal(problemsHash({ status: "due", track: "dsa", pattern: "" }), "#/?track=dsa&status=due");
});

test("no filters write the bare fragment", () => {
  assert.equal(problemsHash({}), "#/");
});

test("problem and attempt fragments read back as their views", () => {
  assert.deepEqual([parseRoute(problemHash("lru-cache")), parseRoute(attemptHash(7))], [
    { view: "problem", slug: "lru-cache" },
    { view: "attempt", id: 7 },
  ]);
});

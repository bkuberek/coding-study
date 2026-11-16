import assert from "node:assert/strict";
import { test } from "node:test";

import { ABOUT_HASH, attemptHash, GUIDES_HASH, guideHash, guidesHash, parseRoute, pathHash, problemHash, problemsHash, setHash, SETS_HASH } from "../src/page/routes.ts";

test("the guides view and a guide and a path have routes of their own", () => {
  assert.deepEqual(
    [parseRoute(GUIDES_HASH), parseRoute(guideHash("hash-functions")), parseRoute(pathHash("hashing"))],
    [{ view: "guides", filters: {} }, { view: "guide", slug: "hash-functions" }, { view: "path", slug: "hashing" }],
  );
});

test("the guides view keeps its search and filters in the fragment's query", () => {
  assert.deepEqual(parseRoute("#/guides?search=hash%20map&level=core&path=hashing&status=not_read&sort=title"), {
    view: "guides",
    filters: { search: "hash map", level: "core", path: "hashing", status: "not_read" },
  });
});

test("the guides view's hash names only what holds a value, the search last as in the problems view's", () => {
  assert.deepEqual(
    [guidesHash({}), guidesHash({ status: "read", search: "", level: "intro" }), guidesHash({ search: "hash map", path: "hashing" })],
    ["#/guides", "#/guides?level=intro&status=read", "#/guides?path=hashing&search=hash+map"],
  );
});

test("a guide's and a path's hashes are the routes `cstudy learn --open` lands on", () => {
  assert.deepEqual([GUIDES_HASH, guideHash("hash-functions"), pathHash("hashing")], ["#/guides", "#/guides/hash-functions", "#/paths/hashing"]);
});

test("a path with no slug, or a guide with more segments, is missing", () => {
  assert.deepEqual([parseRoute("#/paths").view, parseRoute("#/guides/a/b").view], ["missing", "missing"]);
});

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
  assert.deepEqual(parseRoute("#/?sort=title&kind=code-review"), { view: "problems", filters: { kind: "code-review" } });
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

test("about is a view of its own, with a fragment that can be linked", () => {
  assert.deepEqual(parseRoute(ABOUT_HASH), { view: "about" });
  assert.equal(ABOUT_HASH, "#/about");
});

test("about names no more than its own fragment", () => {
  assert.equal(parseRoute("#/about/credits").view, "missing");
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

test("the sets have a view of their own", () => {
  assert.deepEqual(parseRoute(SETS_HASH), { view: "sets" });
});

test("one set is addressed by its name", () => {
  assert.deepEqual(parseRoute(setHash("backend-loop")), { view: "set", name: "backend-loop" });
});

test("a set's name in the fragment is decoded", () => {
  assert.deepEqual(parseRoute("#/sets/a%20b"), { view: "set", name: "a b" });
});

test("anything below a set is no view", () => {
  assert.equal(parseRoute("#/sets/a/b").view, "missing");
});

test("the Set filter is kept in the fragment's query, first", () => {
  assert.equal(problemsHash({ track: "dsa", set: "backend-loop" }), "#/?set=backend-loop&track=dsa");
  assert.deepEqual(parseRoute("#/?set=backend-loop"), { view: "problems", filters: { set: "backend-loop" } });
});

test("the search is kept in the fragment's query", () => {
  assert.deepEqual(parseRoute("#/?search=two%20sum"), { view: "problems", filters: { search: "two sum" } });
  assert.equal(problemsHash({ search: "two sum" }), "#/?search=two+sum");
});

test("the widening is kept in the fragment's query as a comma-separated list in the order lang, role, domain", () => {
  assert.deepEqual(parseRoute("#/?status=due&widen=domain,lang"), { view: "problems", filters: { widen: "lang,domain", status: "due" } });
  assert.equal(problemsHash({ status: "due", widen: "lang,role" }), "#/?widen=lang,role&status=due");
});

test("a widening that names no dimension, or one twice, is dropped or written once; all is every dimension", () => {
  assert.deepEqual(
    [parseRoute("#/?widen=everything"), parseRoute("#/?widen=role,role"), parseRoute("#/?widen=all")],
    [{ view: "problems", filters: {} }, { view: "problems", filters: { widen: "role" } }, { view: "problems", filters: { widen: "lang,role,domain" } }],
  );
});

test("the guides view keeps its domain, role and widening in the query, a guide having no language to widen", () => {
  assert.deepEqual(parseRoute("#/guides?widen=lang,role&level=core&role=backend&domain=security"), {
    view: "guides",
    filters: { domain: "security", role: "backend", widen: "role", level: "core" },
  });
  assert.equal(guidesHash({ search: "hash", level: "advanced", widen: "role", domain: "security" }), "#/guides?domain=security&widen=role&level=advanced&search=hash");
});

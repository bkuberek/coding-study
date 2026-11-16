import assert from "node:assert/strict";
import { test } from "node:test";

import {
  activeGuideFilters,
  countWords,
  isNarrowed,
  narrowListing,
  noMatch,
  pathTitles,
  profileCounts,
  progressText,
  scopeQuery,
  stepCommand,
  stepHref,
  stepTarget,
  wideScopeQuery,
} from "../src/page/guides-model.ts";
import type { GuideEntry, GuideListing, PathStep, PathSummary } from "../src/page/types.ts";

function step(kind: PathStep["kind"], slug: string, level: number | null = null): PathStep {
  return { position: 1, kind, slug, title: slug, level, done: false, status: "new", level_passed: null };
}

test("a guide step opens the guide, a problem step the problem", () => {
  assert.deepEqual([stepHref(step("guide", "hash-functions")), stepHref(step("problem", "two-sum"))], ["#/guides/hash-functions", "#/problems/two-sum"]);
});

test("a step names the command the terminal runs for it, as cstudy learn --path does", () => {
  assert.deepEqual([stepCommand(step("guide", "hash-functions")), stepCommand(step("problem", "two-sum"))], ["cstudy learn hash-functions", "cstudy start two-sum"]);
});

test("a level target reads as the level to pass; no target reads as nothing", () => {
  assert.deepEqual([stepTarget(step("problem", "tamper-evident-ledger", 2)), stepTarget(step("problem", "two-sum"))], ["through level 2", ""]);
});

test("a path's progress reads as steps done of all", () => {
  assert.equal(progressText(3, 21), "3 of 21 steps done");
});

function guide(slug: string, level: GuideEntry["level"], read = false, summary = "A short summary."): GuideEntry {
  return { slug, title: slug.replaceAll("-", " "), summary, level, domains: ["algorithms"], job_roles: ["general"], prerequisites: [], related: [], problems: [], read, read_at: read ? "2026-11-11T09:00:00+00:00" : null };
}

/** What a listing says of the profile when it narrowed nothing. */
const NOT_NARROWED = { languages: null, job_roles: null, domains: null, hidden: { guides: 0, paths: 0 } } as const;

function path(slug: string, level: PathSummary["level"], guides: readonly string[], title = slug): PathSummary {
  return { slug, title, summary: "From the first idea on.", level, guides, done: 0, total: guides.length };
}

const LISTING: GuideListing = {
  guides: [
    guide("using-the-terminal", "intro", true),
    guide("hash-functions", "intro", true, "What a hash function is and why buckets need one."),
    guide("hash-maps-and-sets", "intro"),
    guide("merkle-trees", "advanced", false, "Proofs that a block belongs to a tree."),
    guide("consistent-hashing", "core"),
  ],
  paths: [
    path("getting-started", "intro", ["using-the-terminal"], "Getting started: from the terminal"),
    path("hashing", "core", ["hash-functions", "hash-maps-and-sets", "consistent-hashing", "merkle-trees"], "Hashing: from your first hash map"),
    path("problems-only", null, []),
  ],
  profile: NOT_NARROWED,
};

const slugsOf = (entries: readonly { readonly slug: string }[]): string[] => entries.map((entry) => entry.slug);

test("with no search or filter everything shows, in the listing's order", () => {
  const found = narrowListing(LISTING, {});
  assert.deepEqual([slugsOf(found.guides), slugsOf(found.paths)], [slugsOf(LISTING.guides), slugsOf(LISTING.paths)]);
});

test("a search finds guides and paths by title, summary or slug, in any case", () => {
  assert.deepEqual(
    [
      slugsOf(narrowListing(LISTING, { search: "MERKLE" }).guides),
      slugsOf(narrowListing(LISTING, { search: "buckets" }).guides),
      slugsOf(narrowListing(LISTING, { search: "maps-and" }).guides),
      slugsOf(narrowListing(LISTING, { search: "terminal" }).paths),
    ],
    [["merkle-trees"], ["hash-functions"], ["hash-maps-and-sets"], ["getting-started"]],
  );
});

test("every word of a search must be found, each in any of the fields", () => {
  assert.deepEqual(slugsOf(narrowListing(LISTING, { search: "  hash   buckets " }).guides), ["hash-functions"]);
});

test("a blank search narrows nothing", () => {
  assert.equal(narrowListing(LISTING, { search: "   " }).guides.length, LISTING.guides.length);
});

test("the level keeps the guides and the paths at that level", () => {
  const found = narrowListing(LISTING, { level: "core" });
  assert.deepEqual([slugsOf(found.guides), slugsOf(found.paths)], [["consistent-hashing"], ["hashing"]]);
});

test("the path keeps that path and its guides, in the path's order", () => {
  const found = narrowListing(LISTING, { path: "hashing" });
  assert.deepEqual([slugsOf(found.guides), slugsOf(found.paths)], [["hash-functions", "hash-maps-and-sets", "consistent-hashing", "merkle-trees"], ["hashing"]]);
});

test("a path the listing does not have keeps nothing", () => {
  const found = narrowListing(LISTING, { path: "gone" });
  assert.deepEqual([found.guides.length, found.paths.length], [0, 0]);
});

test("status read keeps the read guides and the paths whose guides are all read", () => {
  const found = narrowListing(LISTING, { status: "read" });
  assert.deepEqual([slugsOf(found.guides), slugsOf(found.paths)], [["using-the-terminal", "hash-functions"], ["getting-started"]]);
});

test("status not read keeps the unread guides and the paths with a guide left to read", () => {
  const found = narrowListing(LISTING, { status: "not_read" });
  assert.deepEqual([slugsOf(found.guides), slugsOf(found.paths)], [["hash-maps-and-sets", "merkle-trees", "consistent-hashing"], ["hashing"]]);
});

test("the search and the filters combine", () => {
  const found = narrowListing(LISTING, { search: "hash", level: "intro", path: "hashing", status: "not_read" });
  assert.deepEqual([slugsOf(found.guides), slugsOf(found.paths)], [["hash-maps-and-sets"], []]);
});

test("a level or a status no choice offers keeps nothing", () => {
  assert.deepEqual([narrowListing(LISTING, { level: "expert" }).guides.length, narrowListing(LISTING, { status: "maybe" }).guides.length], [0, 0]);
});

test("each filter shows as a chip, as the Problems view's read, the path by its title; the search has none", () => {
  const titles = pathTitles(LISTING);
  assert.deepEqual(
    activeGuideFilters({ search: "hash", level: "core", path: "hashing", status: "not_read" }, titles).map((chip) => [chip.key, chip.words]),
    [
      ["level", "level: core"],
      ["path", "path: Hashing: from your first hash map"],
      ["status", "status: not read"],
    ],
  );
});

test("a path the listing does not have reads as its slug", () => {
  assert.deepEqual(activeGuideFilters({ path: "gone" }, pathTitles(LISTING)).map((chip) => chip.words), ["path: gone"]);
});

test("an empty result says what the search and the filters asked", () => {
  const titles = pathTitles(LISTING);
  assert.deepEqual(
    [noMatch("guides", { search: " zebra ", level: "advanced", status: "read" }, titles), noMatch("paths", { level: "advanced" }, titles)],
    ['no guides match "zebra", level: advanced, status: read', "no paths match level: advanced"],
  );
});

test("an empty section with nothing asked says there are none", () => {
  assert.equal(noMatch("guides", { search: "  " }, pathTitles(LISTING)), "no guides");
});

test("the count reads what shows of the whole listing", () => {
  const small: GuideListing = { guides: LISTING.guides.slice(0, 1), paths: LISTING.paths.slice(0, 1), profile: NOT_NARROWED };
  assert.deepEqual(
    [countWords(narrowListing(LISTING, { level: "core" }), LISTING), countWords(narrowListing(small, {}), small)],
    ["1 of 5 guides · 1 of 3 paths", "1 of 1 guide · 1 of 1 path"],
  );
});

test("the view is narrowed while a search, a filter or a widening holds a value", () => {
  assert.deepEqual(
    [isNarrowed({}), isNarrowed({ search: "  " }), isNarrowed({ search: "hash" }), isNarrowed({ status: "read" }), isNarrowed({ domain: "security" }), isNarrowed({ widen: "role" })],
    [false, false, true, true, true, true],
  );
});

test("the domain and the role show as chips, in the route's order before the level", () => {
  assert.deepEqual(
    activeGuideFilters({ level: "core", role: "backend", domain: "security", widen: "role" }, pathTitles(LISTING)).map((chip) => [chip.key, chip.words]),
    [
      ["domain", "domain: security"],
      ["role", "role: backend"],
      ["level", "level: core"],
    ],
  );
});

test("the server narrows by the labels and the widening only, so a change of the level asks it nothing", () => {
  assert.deepEqual(
    [scopeQuery({}), scopeQuery({ level: "core", search: "hash" }), scopeQuery({ domain: "security", role: "backend", widen: "role" }), scopeQuery({ widen: "role,domain" })],
    ["", "", "?domain=security&role=backend", "?widen=role&widen=domain"],
  );
});

test("the listing the chip counts against drops the profile but keeps what the route names", () => {
  assert.deepEqual(
    [wideScopeQuery({}), wideScopeQuery({ level: "core" }), wideScopeQuery({ domain: "security" }), wideScopeQuery({ role: "backend", widen: "domain" })],
    ["?widen=role&widen=domain", "?widen=role&widen=domain", "?domain=security&widen=role", "?role=backend&widen=domain"],
  );
});

/** A listing of the guides and paths the profile of a test keeps, whatever it narrowed. */
function kept(guides: readonly string[], paths: readonly string[]): GuideListing {
  return {
    guides: LISTING.guides.filter((entry) => guides.includes(entry.slug)),
    paths: LISTING.paths.filter((entry) => paths.includes(entry.slug)),
    profile: { languages: null, job_roles: null, domains: ["security"], hidden: { guides: 0, paths: 0 } },
  };
}

test("the profile counts what it keeps of what the filters but the search leave, guides and paths apart", () => {
  const scoped = kept(["hash-functions", "merkle-trees"], ["hashing"]);
  assert.deepEqual(profileCounts(LISTING, scoped, {}), [
    { shown: 2, whole: 5, noun: "guides" },
    { shown: 1, whole: 3, noun: "paths" },
  ]);
  assert.deepEqual(profileCounts(LISTING, scoped, { level: "advanced", search: "nothing of the kind" }), [
    { shown: 1, whole: 1, noun: "guides" },
    { shown: 0, whole: 0, noun: "paths" },
  ]);
});

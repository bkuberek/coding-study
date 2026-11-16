import assert from "node:assert/strict";
import { test } from "node:test";

import {
  activeFilters,
  ALL_PROBLEMS,
  ANY,
  apiQuery,
  DIMENSIONS,
  LABEL_DIMENSIONS,
  listShape,
  type Narrowing,
  NARROWS_NOTHING,
  narrowedBy,
  profileChip,
  sessionNarrowing,
  unwidened,
  widenedBy,
  widenedChips,
  widenedDimensions,
  widenFlags,
  withChoice,
  widenText,
} from "../src/page/filter-model.ts";

const SESSION = {
  languages: ["python", "typescript", "java", "kotlin", "go", "rust"],
  job_roles: ["backend", "frontend", "general", "platform"],
  domains: ["algorithms", "backend", "security"],
};
const everything = { languages: SESSION.languages, job_roles: ["backend", "frontend", "platform"], domains: SESSION.domains };
const BACKEND_ONLY: Narrowing = { lang: null, role: ["backend"], domain: null };
const PY_GO: Narrowing = { lang: ["python", "go"], role: ["backend"], domain: null };

test("the widening is read in the order lang, role, domain, each once, only for the dimensions a view widens", () => {
  assert.deepEqual(
    [
      widenedDimensions("domain,lang"),
      widenedDimensions("role,role"),
      widenedDimensions("lang,role", LABEL_DIMENSIONS),
      widenedDimensions("all"),
      widenedDimensions("all", LABEL_DIMENSIONS),
      widenedDimensions("nothing"),
      widenedDimensions(undefined),
    ],
    [["lang", "domain"], ["role"], ["role"], ["lang", "role", "domain"], ["role", "domain"], [], []],
  );
});

test("the widening is written in the same order, so a route reads back as it was written", () => {
  assert.equal(widenText(["domain", "lang"]), "lang,domain");
  assert.equal(widenText([]), "");
});

test("a profile narrows a dimension when it holds fewer values than the session lists; roles are counted without general", () => {
  assert.deepEqual(sessionNarrowing({ ...SESSION, profile: { ...everything, languages_chosen: false, default_language: "python" } }), NARROWS_NOTHING);
  assert.deepEqual(
    sessionNarrowing({ ...SESSION, profile: { languages: ["python", "go"], languages_chosen: true, default_language: "python", job_roles: ["backend"], domains: ["security"] } }),
    { lang: ["python", "go"], role: ["backend"], domain: ["security"] },
  );
});

test("the dimensions a list answered narrowed are those the server names", () => {
  assert.deepEqual(narrowedBy({ languages: ["python"], job_roles: null, domains: ["security"] }), { lang: ["python"], role: null, domain: ["security"] });
});

const CHOICES = [
  { value: "backend", words: "backend" },
  { value: "platform", words: "platform" },
];

test("while the profile narrows a dimension its list offers your profile, then any, then each value", () => {
  const shape = listShape("role", "role", CHOICES, {}, BACKEND_ONLY);
  assert.deepEqual(shape.options.map((option) => option.words), ["your profile", "any", "backend", "platform"]);
  assert.equal(shape.value, "");
});

test("a profile list holds your profile, any or the value the route names", () => {
  assert.deepEqual(
    [
      listShape("role", "role", CHOICES, {}, BACKEND_ONLY).value,
      listShape("role", "role", CHOICES, { widen: "role" }, BACKEND_ONLY).value,
      listShape("role", "role", CHOICES, { role: "platform" }, BACKEND_ONLY).value,
      listShape("role", "role", CHOICES, { role: "platform", widen: "role" }, BACKEND_ONLY).value,
    ],
    ["", ANY, "platform", "platform"],
  );
});

test("while the profile does not narrow a dimension its list is an ordinary one reading its name", () => {
  const shape = listShape("role", "role", CHOICES, {}, NARROWS_NOTHING);
  assert.deepEqual([shape.options.map((option) => option.words), shape.value], [["role", "backend", "platform"], ""]);
  assert.deepEqual(listShape("track", "any", CHOICES, {}, BACKEND_ONLY).options.map((option) => option.words), ["any", "backend", "platform"]);
});

test("a list a view cannot widen is ordinary whatever the profile narrows", () => {
  assert.equal(listShape("lang", "lang", CHOICES, {}, PY_GO, LABEL_DIMENSIONS).options[0]?.words, "lang");
});

test("a value the route names that the choices lack stays a choice", () => {
  assert.deepEqual(listShape("domain", "domain", CHOICES, { domain: "fintech" }, NARROWS_NOTHING).options.map((option) => option.value), ["", "fintech", "backend", "platform"]);
});

test("choosing any widens the dimension in the route and empties its value", () => {
  assert.deepEqual(withChoice({ role: "platform", status: "due" }, "role", ANY, BACKEND_ONLY), { role: "", status: "due", widen: "role" });
  assert.deepEqual(withChoice({ widen: "lang" }, "role", ANY, PY_GO), { widen: "lang,role", role: "" });
});

test("choosing your profile or a value ends the widening of that dimension, and no other", () => {
  assert.deepEqual(withChoice({ widen: "lang,role" }, "role", "", PY_GO), { widen: "lang", role: "" });
  assert.deepEqual(withChoice({ widen: "role" }, "role", "platform", BACKEND_ONLY), { widen: "", role: "platform" });
});

test("a list that is no profile dimension, or that the profile does not narrow, only takes its value", () => {
  assert.deepEqual(withChoice({ widen: "role" }, "status", "due", BACKEND_ONLY), { widen: "role", status: "due" });
  assert.deepEqual(withChoice({}, "domain", "security", BACKEND_ONLY), { domain: "security" });
});

test("the active filters follow the keys' order, without the search and the widening", () => {
  assert.deepEqual(activeFilters({ search: "two", widen: "lang", domain: "backend", lang: "go" }, ["widen", "lang", "domain", "search"]), [
    { key: "lang", value: "go", words: "lang: go" },
    { key: "domain", value: "backend", words: "domain: backend" },
  ]);
});

test("the checked filter is a chip like the others", () => {
  assert.deepEqual(activeFilters({ checked: "rubric" }, ["checked"]), [{ key: "checked", value: "rubric", words: "checked: rubric" }]);
});

test("a filter's chip reads its value as the view describes it", () => {
  assert.deepEqual(activeFilters({ status: "in_progress" }, ["status"], (_key, value) => value.replace("_", " ")), [{ key: "status", value: "in_progress", words: "status: in progress" }]);
  assert.deepEqual(activeFilters({}, ["status"]), []);
});

test("a widened dimension has a chip, unless the route names a value for it", () => {
  assert.deepEqual(widenedChips({ widen: "lang,role,domain", role: "platform" }), [
    { dimension: "lang", words: "language: any" },
    { dimension: "domain", words: "domain: any" },
  ]);
  assert.deepEqual(widenedChips({ widen: "lang,role" }, LABEL_DIMENSIONS), [{ dimension: "role", words: "role: any" }]);
});

test("removing a widened chip gives the dimension back to the profile", () => {
  assert.deepEqual(unwidened({ widen: "lang,role", status: "due" }, "lang"), { widen: "role", status: "due" });
});

test("the profile chip reads the counts, then the values of each dimension that narrowed", () => {
  const chip = profileChip([{ shown: 120, whole: 400, noun: null }], PY_GO);
  assert.equal(chip?.text, "120 of 400 · your profile: python, go · backend");
  assert.deepEqual(chip?.dimensions, ["lang", "role"]);
});

test("the profile chip's name says what widens, the counts and the dimensions, with general beside the roles", () => {
  assert.equal(
    profileChip([{ shown: 120, whole: 400, noun: null }], PY_GO)?.name,
    "Show all 400: your profile shows 120, languages python, go; roles backend and general",
  );
});

test("a chip of two lists counts each with its noun", () => {
  const chip = profileChip(
    [
      { shown: 40, whole: 132, noun: "guides" },
      { shown: 9, whole: 20, noun: "paths" },
    ],
    { lang: null, role: null, domain: ["security"] },
  );
  assert.deepEqual([chip?.text, chip?.name], [
    "40 of 132 guides · 9 of 20 paths · your profile: security",
    "Show all 132 guides and 20 paths: your profile shows 40 guides and 9 paths, domains security",
  ]);
});

test("the chip shows while only one of two lists lost a row, and not while the profile hid nothing", () => {
  const security: Narrowing = { lang: null, role: null, domain: ["security"] };
  assert.notEqual(
    profileChip(
      [
        { shown: 132, whole: 132, noun: "guides" },
        { shown: 9, whole: 20, noun: "paths" },
      ],
      security,
    ),
    null,
  );
  assert.equal(profileChip([{ shown: 400, whole: 400, noun: null }], PY_GO), null);
});

test("there is no chip while no dimension narrowed this run", () => {
  assert.equal(profileChip([{ shown: 120, whole: 400, noun: null }], NARROWS_NOTHING), null);
});

test("the chip widens each dimension it names and keeps the widening the route had", () => {
  const chip = profileChip([{ shown: 120, whole: 400, noun: null }], PY_GO);
  assert.ok(chip);
  assert.deepEqual(widenedBy({ widen: "domain", status: "due" }, chip), { widen: "lang,role,domain", status: "due" });
  assert.deepEqual(widenedBy({}, chip, LABEL_DIMENSIONS), { widen: "role" });
});

test("a command widens one flag per dimension it takes, or all of them", () => {
  assert.deepEqual(
    [
      widenFlags({}, DIMENSIONS),
      widenFlags({ widen: "lang" }, DIMENSIONS),
      widenFlags({ widen: "lang,domain" }, DIMENSIONS),
      widenFlags({ widen: "lang,role,domain" }, DIMENSIONS),
      widenFlags({ widen: "lang,role" }, LABEL_DIMENSIONS),
      widenFlags({ widen: "role,domain" }, LABEL_DIMENSIONS),
    ],
    [[], ["--widen lang"], ["--widen lang", "--widen domain"], ["--widen all"], ["--widen role"], ["--widen all"]],
  );
});

test("the server is asked for each filter the route names and each dimension it widens that the endpoint takes", () => {
  assert.equal(apiQuery({ status: "due", widen: "lang,role", search: "two" }, ["widen", "status", "search"], DIMENSIONS), "?widen=lang&widen=role&status=due&search=two");
  assert.equal(apiQuery({ widen: "lang,role", track: "dsa" }, ["track", "widen"], LABEL_DIMENSIONS), "?track=dsa&widen=role");
  assert.equal(apiQuery({}, ["status", "widen"], DIMENSIONS), "");
});

test("a dimension the route names a value for is not widened in the query", () => {
  assert.equal(apiQuery({ widen: "lang,role", lang: "go" }, ["widen", "lang"], DIMENSIONS), "?widen=role&lang=go");
});

test("the whole list of problems widens every dimension", () => {
  assert.equal(ALL_PROBLEMS, "/api/v1/problems?widen=lang&widen=role&widen=domain");
});

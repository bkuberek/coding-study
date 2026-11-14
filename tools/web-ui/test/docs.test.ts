import assert from "node:assert/strict";
import { test } from "node:test";

import { inSections, neighbours, searchDocs, snippetOf, type DocSummary } from "../src/page/docs-model.ts";
import { docHash, docsHash, parseRoute } from "../src/page/routes.ts";

function page(slug: string, section: string, order: number, passages: readonly [string, string, string][] = []): DocSummary {
  return {
    slug,
    title: slug.toUpperCase(),
    summary: `About ${slug}.`,
    section,
    order,
    headings: passages.filter(([id]) => id !== "").map(([id, title]) => ({ id, title, level: 2 })),
    passages: passages.map(([id, title, text]) => ({ id, title, text })),
  };
}

const DOCTOR = page("doctor", "Start here", 30, [
  ["", "DOCTOR", "About the doctor. It checks each tool and prints a fix."],
  ["the-rows", "The rows", "ok means the check passed; FAIL blocks practice."],
  ["fix", "Set up and repair with --fix", "Run uv sync and pnpm install, then the Gradle warm-up."],
]);
const START = page("getting-started", "Start here", 10, [["", "GETTING-STARTED", "Install cstudy, then run the doctor."]]);
const WEB = page("web-ui", "The web UI", 100, [["keyboard", "Keyboard", "Alt+8 opens the docs."]]);
const PAGES = [WEB, DOCTOR, START];

test("the docs routes: the list with its search, a page, and a page at a heading", () => {
  assert.deepEqual(
    [parseRoute("#/docs"), parseRoute("#/docs?search=gradle%20warm"), parseRoute("#/docs/doctor"), parseRoute("#/docs/doctor/the-rows"), parseRoute("#/docs/a/b/c")],
    [
      { view: "docs", search: "" },
      { view: "docs", search: "gradle warm" },
      { view: "doc", slug: "doctor", heading: null },
      { view: "doc", slug: "doctor", heading: "the-rows" },
      { view: "missing", fragment: "#/docs/a/b/c" },
    ],
  );
});

test("a docs route is made from a page and a heading, and the list from its search", () => {
  assert.deepEqual(
    [docHash("doctor"), docHash("toolchains", "nodejs-and-pnpm"), docHash("doctor", "--fix"), docsHash(""), docsHash("gradle warm")],
    ["#/docs/doctor", "#/docs/toolchains/nodejs-and-pnpm", "#/docs/doctor/--fix", "#/docs", "#/docs?search=gradle+warm"],
  );
});

test("the pages are grouped by section, each section where its first page is", () => {
  assert.deepEqual(
    inSections(PAGES).map(({ section, pages }) => [section, pages.map((found) => found.slug)]),
    [
      ["Start here", ["getting-started", "doctor"]],
      ["The web UI", ["web-ui"]],
    ],
  );
});

test("a page's neighbours are the pages before and after it by order", () => {
  assert.deepEqual(
    [neighbours(PAGES, "getting-started"), neighbours(PAGES, "doctor"), neighbours(PAGES, "nope")].map(({ previous, next }) => [previous?.slug ?? null, next?.slug ?? null]),
    [
      [null, "doctor"],
      ["getting-started", "web-ui"],
      [null, null],
    ],
  );
});

test("a search finds each passage that holds every word, in any case, in page order", () => {
  assert.deepEqual(
    searchDocs(PAGES, "  the DOCTOR ").map((result) => [result.slug, result.heading, result.title]),
    [
      ["getting-started", "", "GETTING-STARTED"],
      ["doctor", "", "DOCTOR"],
    ],
  );
});

test("a search matches a heading's words too, and nothing for no words", () => {
  assert.deepEqual(
    [searchDocs(PAGES, "repair gradle").map((result) => [result.slug, result.heading]), searchDocs(PAGES, "   "), searchDocs(PAGES, "zebra")],
    [[["doctor", "fix"]], [], []],
  );
});

test("a result shows the words around the first match", () => {
  const [found] = searchDocs(PAGES, "pnpm");
  assert.deepEqual(found?.snippet, { before: "Run uv sync and ", match: "pnpm", after: " install, then the Gradle warm-up." });
});

test("a long text is cut around the match, with an ellipsis at each cut end", () => {
  const text = `${"a ".repeat(60)}needle${" b".repeat(60)}`;
  const snippet = snippetOf(text, "needle", 20);
  assert.deepEqual([snippet.before.startsWith("…"), snippet.match, snippet.after.endsWith("…"), snippet.before.length <= 21, snippet.after.length <= 21], [true, "needle", true, true, true]);
});

test("a match only in the heading shows the start of the text", () => {
  assert.deepEqual(snippetOf("Some words here.", "absent", 40), { before: "", match: "", after: "Some words here." });
});

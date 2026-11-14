/**
 * The Docs view (docs/specs/user-docs.md#docs-view): the user docs that `cstudy docs` reads, the
 * pages by section with a search over their passages, and a page rendered on the server, with
 * its headings to jump to, every other page beside it, and the previous and next page.
 */

import "./docs.css";

import type { Cleanup, PageContext } from "../context.ts";
import { h, isTyping, rendered } from "../dom.ts";
import { type DocDocument, type DocResult, type DocsListing, type DocSummary, inSections, neighbours, searchDocs } from "../docs-model.ts";
import { DOCS_HASH, docHash, docsHash } from "../routes.ts";
import { empty, loading, showFailure } from "../states.ts";

const DOCS_API = "/api/v1/docs";
const SEARCH_FIELD = "docs-search";
const HEADING_ID = (heading: string): string => `doc-${heading}`;

/** The listing and the pages read so far: the docs ship with cstudy, so they do not change while
 * the page is open, and going from one heading to another draws at once. */
let listing: Promise<DocsListing> | null = null;
const pages = new Map<string, Promise<DocDocument>>();

function loadListing(context: PageContext): Promise<DocsListing> {
  listing ??= context.api.get<DocsListing>(DOCS_API).catch((error: unknown) => {
    listing = null;
    throw error;
  });
  return listing;
}

function loadPage(context: PageContext, slug: string): Promise<DocDocument> {
  let found = pages.get(slug);
  if (found === undefined) {
    found = context.api.get<DocDocument>(`${DOCS_API}/${encodeURIComponent(slug)}`).catch((error: unknown) => {
      pages.delete(slug);
      throw error;
    });
    pages.set(slug, found);
  }
  return found;
}

function sectionList(found: DocsListing): HTMLElement[] {
  return inSections(found.pages).map(({ section, pages: members }, index) =>
    h(
      "section",
      { class: "doc-section", "aria-labelledby": `doc-section-${index}` },
      h("h2", { id: `doc-section-${index}` }, section),
      h(
        "ul",
        { class: "plain doc-list" },
        ...members.map((page) => h("li", {}, h("a", { href: docHash(page.slug), class: "doc-title" }, page.title), h("p", { class: "quiet" }, page.summary))),
      ),
    ),
  );
}

function resultRow(result: DocResult): HTMLElement {
  const { before, match, after } = result.snippet;
  return h(
    "li",
    { class: "doc-result" },
    h(
      "a",
      { href: docHash(result.slug, result.heading), class: "doc-title" },
      result.page,
      result.heading === "" ? null : h("span", { class: "doc-result-heading" }, h("span", { "aria-hidden": "true" }, " › "), h("span", { class: "sr-only" }, ", "), result.title),
    ),
    h("p", { class: "quiet doc-snippet" }, before, match ? h("mark", {}, match) : null, after),
  );
}

function countText(results: readonly DocResult[], search: string): string {
  if (results.length === 0) return `nothing matches “${search}”`;
  return results.length === 1 ? "1 section matches" : `${results.length} sections match`;
}

/** The list: every page by section, or the sections a search finds. */
export function docsView(context: PageContext, search: string): Cleanup {
  const { shell } = context;
  shell.setView("docs");
  shell.setCommand("cstudy docs");
  shell.setStatus({ mode: "DOCS", where: "how to use cstudy" });
  const field = h("input", {
    id: SEARCH_FIELD,
    type: "search",
    value: search,
    placeholder: "search docs…",
    autocomplete: "off",
    spellcheck: "false",
    "aria-keyshortcuts": "/",
    "aria-describedby": "docs-count",
  });
  const count = h("p", { id: "docs-count", class: "quiet docs-count", role: "status" });
  const body = h("div", { class: "docs-body" }, loading());
  shell.main.replaceChildren(
    h(
      "section",
      { class: "docs", "aria-labelledby": "docs-heading" },
      h("header", { class: "view-head" }, h("h1", { id: "docs-heading" }, "docs")),
      h("p", { class: "docs-intro" }, "How to use cstudy, from the first install to troubleshooting. The terminal reads the same pages: ", h("code", { class: "cmd" }, "cstudy docs <topic>"), "."),
      h("div", { class: "docs-search" }, h("label", { for: SEARCH_FIELD, class: "sr-only" }, "Search the docs"), field),
      count,
      body,
    ),
  );
  let left = false;
  let found: DocsListing | null = null;
  const draw = () => {
    if (found === null) return;
    const text = field.value.trim();
    if (text === "") {
      count.textContent = "";
      body.replaceChildren(...(found.pages.length ? sectionList(found) : [empty("There are no docs in this content root.")]));
      return;
    }
    const results = searchDocs(found.pages, text);
    count.textContent = countText(results, text);
    body.replaceChildren(results.length ? h("ol", { class: "plain doc-results", "aria-label": "Search results" }, ...results.map(resultRow)) : empty("Try fewer words, or other words."));
  };
  field.addEventListener("input", () => {
    history.replaceState(null, "", docsHash(field.value.trim()));
    draw();
  });
  void loadListing(context)
    .then((loaded) => {
      if (left) return;
      found = loaded;
      draw();
    })
    .catch((error: unknown) => {
      if (!left) showFailure(body, error);
    });
  const focusSearch = (event: KeyboardEvent) => {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target) || document.querySelector("dialog[open]")) return;
    event.preventDefault();
    field.focus();
  };
  document.addEventListener("keydown", focusSearch);
  return () => {
    left = true;
    document.removeEventListener("keydown", focusSearch);
  };
}

function headingLinks(page: DocDocument): HTMLElement | null {
  const shown = page.headings.filter((heading) => heading.level === 2);
  if (shown.length === 0) return null;
  return h(
    "nav",
    { class: "side-block", "aria-labelledby": "doc-contents" },
    h("h2", { id: "doc-contents", class: "eyebrow" }, "on this page"),
    h("ul", { class: "plain doc-contents" }, ...shown.map((heading) => h("li", {}, h("a", { href: docHash(page.slug, heading.id) }, heading.title)))),
  );
}

function allPages(found: DocsListing, slug: string): HTMLElement {
  return h(
    "nav",
    { class: "side-block doc-all", "aria-labelledby": "doc-all-heading" },
    h("h2", { id: "doc-all-heading", class: "eyebrow" }, "all docs"),
    ...inSections(found.pages).map(({ section, pages: members }) =>
      h(
        "div",
        { class: "doc-group" },
        h("p", { class: "doc-group-name" }, section),
        h("ul", { class: "plain" }, ...members.map((page: DocSummary) => h("li", {}, h("a", { href: docHash(page.slug), "aria-current": page.slug === slug ? "page" : false }, page.title)))),
      ),
    ),
  );
}

function pager(found: DocsListing, slug: string): HTMLElement | null {
  const { previous, next } = neighbours(found.pages, slug);
  if (previous === null && next === null) return null;
  return h(
    "nav",
    { class: "doc-pager", "aria-label": "Previous and next page" },
    previous ? h("a", { href: docHash(previous.slug), class: "doc-previous" }, h("span", { class: "quiet" }, "previous"), previous.title) : h("span", {}),
    next ? h("a", { href: docHash(next.slug), class: "doc-next" }, h("span", { class: "quiet" }, "next"), next.title) : null,
  );
}

/** Scrolls the heading the route names clear of the top bar and gives it the focus, so the
 * keyboard and a screen reader carry on from there. */
function showHeading(page: HTMLElement, heading: string | null): void {
  if (heading === null) return;
  const target = page.querySelector<HTMLElement>(`#${CSS.escape(HEADING_ID(heading))}`);
  if (target === null) return;
  target.tabIndex = -1;
  target.scrollIntoView({ block: "start" });
  target.focus({ preventScroll: true });
}

/** A page, and with `heading` the page at that heading. */
export function docView(context: PageContext, slug: string, heading: string | null): Cleanup {
  const { shell } = context;
  shell.setView("docs");
  shell.setCommand(`cstudy docs ${slug}`);
  shell.setStatus({ mode: "DOCS", where: slug });
  const page = h("article", { class: "doc", "aria-busy": "true" }, loading());
  shell.main.replaceChildren(page);
  let left = false;
  void Promise.all([loadPage(context, slug), loadListing(context)])
    .then(([doc, found]) => {
      if (left) return;
      page.removeAttribute("aria-busy");
      page.replaceChildren(
        h(
          "header",
          { class: "doc-head" },
          h("p", { class: "eyebrow" }, h("a", { href: DOCS_HASH }, "docs"), ` · ${doc.section}`),
          h("h1", {}, doc.title),
          h("p", { class: "doc-summary" }, doc.summary),
        ),
        h(
          "div",
          { class: "doc-grid" },
          h("div", { class: "doc-main" }, rendered(doc.html, "prose doc-body"), pager(found, doc.slug)),
          h("aside", { class: "doc-side", "aria-label": "Contents" }, headingLinks(doc), allPages(found, doc.slug)),
        ),
      );
      document.title = `${doc.title} · cstudy`;
      showHeading(page, heading);
    })
    .catch((error: unknown) => {
      if (!left) showFailure(page, error);
    });
  return () => {
    left = true;
  };
}

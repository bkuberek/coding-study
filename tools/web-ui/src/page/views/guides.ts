/**
 * The Guides view (docs/specs/web-ui.md#guides-view), the recommended way to learn: the paths with
 * their progress and the guides with their read state (`cstudy learn`), narrowed by a search and
 * filters kept in the fragment's query, a guide to read with its
 * diagrams, drawn ahead of time as SVG in the page's light and dark palettes, and a control that
 * marks it read (`cstudy learn <guide>`, `--done`), and a path's steps in order, each done or not,
 * with a link to read the guide or start the problem (`cstudy learn --path <path>`).
 */

import "../filters.css";
import "./guides.css";

import { learnCommand } from "../commands.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { command, h, isSearchShortcut, rendered } from "../dom.ts";
import { exampleTabs } from "../example-tabs.ts";
import { statusWords } from "../format.ts";
import {
  activeGuideFilters,
  countWords,
  isNarrowed,
  LEVELS,
  narrowListing,
  noMatch,
  pathTitles,
  progressText,
  STATUSES,
  stepCommand,
  stepHref,
  stepTarget,
} from "../guides-model.ts";
import { type GuideFilterKey, type GuideFilters, GUIDES_HASH, guideHash, guidesHash, pathHash, problemHash } from "../routes.ts";
import { empty, loading, messageOf, showFailure } from "../states.ts";
import type { GuideDocument, GuideEntry, GuideListing, MarkedRead, PathDocument, PathStep, PathSummary } from "../types.ts";

const GUIDES_API = "/api/v1/guides";
/** The ids of the Problems view's search and filters, which never shows beside this one. */
const SEARCH_FIELD = "filter-search";
type ChoiceKey = Exclude<GuideFilterKey, "search">;
const LEVEL_WORDS: Readonly<Record<GuideEntry["level"], string>> = {
  intro: "intro: a first idea",
  core: "core: used every day",
  advanced: "advanced: beyond the basics",
};

function readDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function readMark(read: boolean): HTMLElement {
  return read
    ? h("span", { class: "read-mark is-read" }, h("span", { "aria-hidden": "true" }, "✓ "), "read")
    : h("span", { class: "read-mark" }, "not read");
}

function progressBar(done: number, total: number): HTMLElement {
  return h("progress", { class: "guide-progress", value: done, max: Math.max(total, 1), "aria-label": progressText(done, total) });
}

function pathCard(path: PathSummary): HTMLElement {
  return h(
    "li",
    { class: "path-card" },
    h("h3", {}, h("a", { href: pathHash(path.slug) }, path.title)),
    h("p", { class: "quiet" }, path.summary),
    path.level ? h("p", { class: "guide-level" }, `level: ${path.level}`) : null,
    h("p", { class: "path-standing" }, progressBar(path.done, path.total), h("span", {}, progressText(path.done, path.total))),
  );
}

function guideRow(guide: GuideEntry): HTMLElement {
  return h(
    "li",
    { class: "guide-row" },
    h("div", { class: "guide-row-head" }, h("a", { href: guideHash(guide.slug), class: "guide-title" }, guide.title), readMark(guide.read)),
    h("p", { class: "quiet" }, guide.summary),
    h("p", { class: "guide-level" }, LEVEL_WORDS[guide.level]),
  );
}

/** A filter's list; the value the route names stays a choice, whatever the list holds. */
function filterSelect(key: ChoiceKey, chosen: string | undefined, choices: readonly (readonly [string, string])[], blank: string): HTMLSelectElement {
  const values = chosen && !choices.some(([value]) => value === chosen) ? [[chosen, chosen] as const, ...choices] : choices;
  return h(
    "select",
    { id: `filter-${key}`, name: key, class: chosen ? "is-set" : null },
    h("option", { value: "" }, blank),
    ...values.map(([value, words]) => h("option", { value, selected: chosen === value }, words)),
  );
}

/**
 * The search, the filters and the lists they narrow, in place: the listing is read once, so typing
 * and choosing ask the server nothing, and the route's query follows each change without adding to
 * the history.
 */
function listing(context: PageContext, found: GuideListing, initial: GuideFilters): HTMLElement[] {
  if (found.guides.length === 0 && found.paths.length === 0) {
    return [empty("There are no guides in this content root yet.", h("p", { class: "quiet" }, command("cstudy learn")))];
  }
  const { shell } = context;
  let filters: GuideFilters = { ...initial };
  const titles = pathTitles(found);
  const pathCards = new Map(found.paths.map((path) => [path.slug, pathCard(path)]));
  const guideRows = new Map(found.guides.map((guide) => [guide.slug, guideRow(guide)]));
  const pathList = h("ul", { class: "plain path-cards" });
  const guideList = h("ul", { class: "plain guide-list" });
  const noPaths = h("p", { class: "quiet guide-none" });
  const noGuides = h("p", { class: "quiet guide-none" });

  const search = h("input", {
    id: SEARCH_FIELD,
    name: "search",
    type: "search",
    value: filters.search ?? "",
    placeholder: "search guides and paths…",
    spellcheck: "false",
    autocomplete: "off",
    "aria-keyshortcuts": "/",
  });
  const selects: Record<ChoiceKey, HTMLSelectElement> = {
    level: filterSelect("level", filters.level, LEVELS.map((level) => [level, level] as const), "level"),
    path: filterSelect("path", filters.path, found.paths.map((path) => [path.slug, path.title] as const), "path"),
    status: filterSelect("status", filters.status, STATUSES.map((status) => [status, statusWords(status)] as const), "status"),
  };
  const form = h(
    "form",
    { class: "filters", role: "search", "aria-label": "Filter guides and paths" },
    h(
      "label",
      { class: "filter-search", for: search.id },
      h("span", { class: "sr-only" }, "Search guides and paths by title, summary or slug"),
      h("span", { class: "filter-prompt", "aria-hidden": "true" }, ">"),
      search,
    ),
    ...(Object.keys(selects) as ChoiceKey[]).map((key) => h("label", { class: "filter", for: `filter-${key}` }, h("span", { class: "sr-only" }, key), selects[key])),
  );
  form.addEventListener("submit", (event) => event.preventDefault());

  const count = h("span", { class: "filter-count" });
  const clear = h("a", { href: GUIDES_HASH, class: "clear" }, "clear");
  const summary = h("div", { class: "filter-summary" });

  const draw = () => {
    const narrowed = narrowListing(found, filters);
    pathList.replaceChildren(...narrowed.paths.flatMap((path) => pathCards.get(path.slug) ?? []));
    guideList.replaceChildren(...narrowed.guides.flatMap((guide) => guideRows.get(guide.slug) ?? []));
    pathList.hidden = narrowed.paths.length === 0;
    guideList.hidden = narrowed.guides.length === 0;
    noPaths.hidden = !pathList.hidden;
    noGuides.hidden = !guideList.hidden;
    noPaths.textContent = noMatch("paths", filters, titles);
    noGuides.textContent = noMatch("guides", filters, titles);
    count.textContent = countWords(narrowed, found);
    const chips = activeGuideFilters(filters, titles).map(({ key, words }, index, active) => {
      const chip = h("button", { type: "button", id: `chip-${key}`, class: "filter-chip", "aria-label": `Remove the filter ${words}` }, words, " ", h("span", { "aria-hidden": "true" }, "×"));
      const neighbour = active[index + 1] ?? active[index - 1];
      chip.addEventListener("click", () => {
        selects[key].value = "";
        change({ [key]: "" });
        (neighbour === undefined ? search : (summary.querySelector<HTMLElement>(`#chip-${neighbour.key}`) ?? search)).focus();
      });
      return chip;
    });
    summary.replaceChildren(...chips, h("span", { class: "filter-tally" }, count, h("span", { class: "quiet" }, " · "), clear));
    const narrowing = isNarrowed(filters);
    summary.hidden = !narrowing;
    shell.setStatus({ mode: "GUIDES", where: narrowing ? count.textContent : "guides and paths" });
    if (narrowing) shell.announce(`showing ${count.textContent}`);
  };
  const change = (changed: GuideFilters) => {
    filters = { ...filters, ...changed };
    for (const key of Object.keys(selects) as ChoiceKey[]) selects[key].classList.toggle("is-set", Boolean(filters[key]));
    const route = { ...filters, search: (filters.search ?? "").trim() };
    history.replaceState(null, "", guidesHash(route));
    shell.setCommand(learnCommand(route));
    draw();
  };
  search.addEventListener("input", () => change({ search: search.value }));
  for (const key of Object.keys(selects) as ChoiceKey[]) selects[key].addEventListener("change", () => change({ [key]: selects[key].value }));
  clear.addEventListener("click", (event) => {
    event.preventDefault();
    search.value = "";
    for (const select of Object.values(selects)) select.value = "";
    change({ search: "", level: "", path: "", status: "" });
    search.focus();
  });
  draw();

  return [
    h("div", { class: "filter-bar" }, form),
    summary,
    h(
      "section",
      { class: "guide-section", "aria-labelledby": "paths-heading" },
      h("h2", { id: "paths-heading" }, "paths"),
      h("p", { class: "quiet" }, "A path puts guides and problems in order, from a topic's first idea to an expert's. The paths run from introductory to advanced."),
      ...(found.paths.length ? [pathList, noPaths] : [empty("no paths yet")]),
    ),
    h("section", { class: "guide-section", "aria-labelledby": "all-guides-heading" }, h("h2", { id: "all-guides-heading" }, "all guides"), guideList, noGuides),
  ];
}

export function guidesView(context: PageContext, filters: GuideFilters): Cleanup {
  const { api, shell } = context;
  shell.setView("guides");
  shell.setCommand(learnCommand(filters));
  shell.setStatus({ mode: "GUIDES", where: "guides and paths" });
  const body = h("div", { class: "guides-body" }, loading());
  shell.main.replaceChildren(
    h(
      "section",
      { class: "guides", "aria-labelledby": "guides-heading" },
      h("header", { class: "view-head" }, h("h1", { id: "guides-heading" }, "guides")),
      h("p", { class: "guides-intro" }, "Short readings that teach an idea before you practise it, with examples and diagrams. Follow a path, or open any guide."),
      body,
    ),
  );
  let left = false;
  void api
    .get<GuideListing>(GUIDES_API)
    .then((found) => {
      if (!left) body.replaceChildren(...listing(context, found, filters));
    })
    .catch((error: unknown) => {
      if (!left) showFailure(body, error);
    });
  const focusSearch = (event: KeyboardEvent) => {
    const field = body.querySelector<HTMLInputElement>(`#${SEARCH_FIELD}`);
    if (field === null || !isSearchShortcut(event)) return;
    event.preventDefault();
    field.focus();
  };
  document.addEventListener("keydown", focusSearch);
  return () => {
    left = true;
    document.removeEventListener("keydown", focusSearch);
  };
}

function guideLinks(title: string, slugs: readonly string[], titles: ReadonlyMap<string, GuideEntry>, id: string): HTMLElement | null {
  if (slugs.length === 0) return null;
  const items = slugs.map((slug) => {
    const known = titles.get(slug);
    return h("li", {}, h("a", { href: guideHash(slug) }, known?.title ?? slug), known?.read ? h("span", { class: "quiet" }, " · read") : null);
  });
  return h("section", { class: "side-block", "aria-labelledby": id }, h("h2", { id, class: "eyebrow" }, title), h("ul", { class: "plain" }, ...items));
}

function practise(problems: readonly string[]): HTMLElement | null {
  if (problems.length === 0) return null;
  return h(
    "section",
    { class: "side-block", "aria-labelledby": "practise-heading" },
    h("h2", { id: "practise-heading", class: "eyebrow" }, "practise"),
    h("ul", { class: "plain" }, ...problems.map((slug) => h("li", {}, h("a", { href: problemHash(slug) }, slug)))),
  );
}

/** The control at the end of a guide: Mark as read, or when it was read. */
function readControl(context: PageContext, guide: GuideDocument, readChanged: (readAt: string) => void): HTMLElement {
  const region = h("div", { class: "guide-read" });
  const showRead = (readAt: string) => region.replaceChildren(h("p", { class: "read-mark is-read" }, h("span", { "aria-hidden": "true" }, "✓ "), `read on ${readDate(readAt)}`));
  if (guide.read_at !== null) {
    showRead(guide.read_at);
    return region;
  }
  const button = h("button", { type: "button", class: "button primary" }, "Mark as read");
  const problem = h("p", { class: "state-error", role: "alert", hidden: true });
  button.addEventListener("click", () => {
    button.disabled = true;
    void context.api
      .post<MarkedRead>(`${GUIDES_API}/${encodeURIComponent(guide.slug)}/read`, {})
      .then((marked) => {
        showRead(marked.read_at);
        readChanged(marked.read_at);
        context.shell.announce(`${guide.title} marked read`);
      })
      .catch((error: unknown) => {
        button.disabled = false;
        problem.hidden = false;
        problem.textContent = `error: ${messageOf(error)}`;
      });
  });
  region.append(h("p", { class: "quiet" }, "Done reading? Marking it read counts it in every path that has it. ", command(`cstudy learn ${guide.slug} --done`)), h("p", {}, button), problem);
  return region;
}

/** A guide, its diagrams as the server's `<img>` pairs, of which the stylesheet shows the one of
 * the page's theme, and its examples in several languages as tabs. */
export function guideView(context: PageContext, slug: string): Cleanup {
  const { api, shell } = context;
  shell.setView("guides");
  shell.setCommand(`cstudy learn ${slug}`);
  shell.setStatus({ mode: "GUIDE", where: slug });
  const page = h("article", { class: "guide", "aria-busy": "true" }, loading());
  shell.main.replaceChildren(page);
  let left = false;
  let stopTabs = (): void => undefined;
  void Promise.all([api.get<GuideDocument>(`${GUIDES_API}/${encodeURIComponent(slug)}`), api.get<GuideListing>(GUIDES_API)])
    .then(([guide, found]) => {
      if (left) return;
      const titles = new Map(found.guides.map((entry) => [entry.slug, entry]));
      const mark = readMark(guide.read_at !== null);
      const body = rendered(guide.html, "prose guide-body");
      stopTabs = exampleTabs(body, context.session.default_lang, (message) => shell.announce(message));
      page.removeAttribute("aria-busy");
      page.replaceChildren(
        h(
          "header",
          { class: "guide-head" },
          h("p", { class: "eyebrow" }, h("a", { href: GUIDES_HASH }, "guides"), ` · ${LEVEL_WORDS[guide.level]}`),
          h("h1", {}, guide.title),
          h("p", { class: "guide-summary" }, guide.summary),
          h("p", {}, mark),
        ),
        h(
          "div",
          { class: "guide-grid" },
          h("div", { class: "guide-main" }, body, readControl(context, guide, () => mark.replaceWith(readMark(true)))),
          h(
            "aside",
            { class: "guide-side", "aria-label": "Related" },
            guideLinks("read first", guide.prerequisites, titles, "before-heading"),
            practise(guide.problems),
            guideLinks("read next", guide.related, titles, "next-heading"),
          ),
        ),
      );
      document.title = `${guide.title} · cstudy`;
    })
    .catch((error: unknown) => {
      if (!left) showFailure(page, error);
    });
  return () => {
    left = true;
    stopTabs();
  };
}

function stepRow(step: PathStep): HTMLElement {
  const target = stepTarget(step);
  const action = step.kind === "guide" ? (step.done ? "Read again" : "Read") : step.done ? "Practise again" : "Start";
  return h(
    "li",
    { class: step.done ? "path-step is-done" : "path-step" },
    h("span", { class: "step-mark", "aria-hidden": "true" }, step.done ? "✓" : String(step.position)),
    h(
      "div",
      { class: "step-body" },
      h("p", { class: "step-head" }, h("span", { class: "step-kind" }, step.kind), h("a", { href: stepHref(step) }, step.title), target ? h("span", { class: "step-target" }, target) : null),
      h("p", { class: "step-status quiet" }, h("span", { class: "sr-only" }, step.done ? "done: " : "not done: "), step.status, " · ", command(stepCommand(step))),
    ),
    h("a", { href: stepHref(step), class: "button step-action", "aria-label": `${action}: ${step.title}` }, action),
  );
}

export function pathView(context: PageContext, slug: string): Cleanup {
  const { api, shell } = context;
  shell.setView("guides");
  shell.setCommand(`cstudy learn --path ${slug}`);
  shell.setStatus({ mode: "PATH", where: slug });
  const page = h("article", { class: "path", "aria-busy": "true" }, loading());
  shell.main.replaceChildren(page);
  let left = false;
  void api
    .get<PathDocument>(`/api/v1/paths/${encodeURIComponent(slug)}`)
    .then((path) => {
      if (left) return;
      page.removeAttribute("aria-busy");
      const next = path.next;
      page.replaceChildren(
        h(
          "header",
          { class: "guide-head" },
          h("p", { class: "eyebrow" }, h("a", { href: GUIDES_HASH }, "guides"), " · path"),
          h("h1", {}, path.title),
          h("p", { class: "guide-summary" }, path.summary),
          h("p", { class: "path-standing" }, progressBar(path.done, path.total), h("span", {}, progressText(path.done, path.total))),
          next
            ? h("p", { class: "path-next" }, h("span", { class: "quiet" }, "next: "), h("a", { href: stepHref(next) }, next.title), " ", command(stepCommand(next)))
            : h("p", { class: "path-next" }, "Every step is done."),
        ),
        h("ol", { class: "plain path-steps", "aria-label": "Steps" }, ...path.steps.map(stepRow)),
      );
      shell.setStatus({ mode: "PATH", where: `${slug} · ${progressText(path.done, path.total)}` });
      document.title = `${path.title} · cstudy`;
    })
    .catch((error: unknown) => {
      if (!left) showFailure(page, error);
    });
  return () => {
    left = true;
  };
}

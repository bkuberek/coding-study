/**
 * The Guides view (docs/specs/web-ui.md#guides-view), the recommended way to learn: the paths with
 * their progress and the guides with their read state (`cstudy learn`), narrowed by a search and
 * filters kept in the fragment's query, a guide to read with its
 * diagrams, drawn ahead of time as SVG in the page's light and dark palettes, and a control that
 * marks it read (`cstudy learn <guide>`, `--done`), and a path's steps in order, each done or not,
 * with a link to read the guide or start the problem (`cstudy learn --path <path>`).
 */

import "./guides.css";

import { learnCommand } from "../commands.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { command, h, rendered } from "../dom.ts";
import { exampleTabs } from "../example-tabs.ts";
import { filterBar, type ListFilter } from "../filter-bar.ts";
import { type FilterValues, LABEL_DIMENSIONS, narrowedBy, profileChip, sessionNarrowing, wideQuery } from "../filter-model.ts";
import { statusWords } from "../format.ts";
import {
  countWords,
  describeGuideFilter,
  isNarrowed,
  LEVELS,
  narrowListing,
  noMatch,
  pathTitles,
  profileCounts,
  progressText,
  scopeQuery,
  STATUSES,
  stepCommand,
  stepHref,
  stepTarget,
  wideScopeQuery,
} from "../guides-model.ts";
import { GUIDE_FILTER_KEYS, type GuideFilters, GUIDES_HASH, guideHash, guidesHash, pathHash, problemHash } from "../routes.ts";
import { empty, loading, messageOf, showFailure } from "../states.ts";
import type { GuideDocument, GuideEntry, GuideListing, MarkedRead, PathDocument, PathStep, PathSummary } from "../types.ts";

const GUIDES_API = "/api/v1/guides";
/** The whole listing, which ignores the profile: the count's whole, the titles of a guide's links. */
const WHOLE_QUERY = wideQuery(LABEL_DIMENSIONS);
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

/** What the Guides view holds of the server's listings: the whole one, which ignores the profile
 * and the filters; the one the route's domain, role and widening ask for; and that one with the
 * profile dropped, which the profile chip counts against. */
interface Listings {
  readonly whole: GuideListing;
  readonly scoped: GuideListing;
  readonly wide: GuideListing;
}

type Read = (query: string) => Promise<GuideListing>;

/**
 * The search, the filters and the lists they narrow, in place: the search, the level, the path and
 * the status narrow the listing already read, so typing and choosing ask the server nothing; a
 * change of the domain, the role or the widening reads the listing that scope asks for, which the
 * server narrows by the labels of the guides and of each path's steps. The route's query follows
 * each change without adding to the history.
 */
function listing(context: PageContext, held: Listings, initial: GuideFilters, read: Read): { readonly nodes: HTMLElement[]; readonly detach: Cleanup } {
  const { whole } = held;
  if (whole.guides.length === 0 && whole.paths.length === 0) {
    return { nodes: [empty("There are no guides in this content root yet.", h("p", { class: "quiet" }, command("cstudy learn")))], detach: () => undefined };
  }
  const { shell, session } = context;
  let { scoped, wide } = held;
  let filters: GuideFilters = { ...initial };
  let reading = 0;
  const titles = pathTitles(whole);
  const pathCards = new Map(whole.paths.map((path) => [path.slug, pathCard(path)]));
  const guideRows = new Map(whole.guides.map((guide) => [guide.slug, guideRow(guide)]));
  const pathList = h("ul", { class: "plain path-cards" });
  const guideList = h("ul", { class: "plain guide-list" });
  const noPaths = h("p", { class: "quiet guide-none" });
  const noGuides = h("p", { class: "quiet guide-none" });

  const named = (values: readonly string[]) => values.map((value) => ({ value, words: value }));
  const lists: ListFilter[] = [
    { key: "domain", choices: named(session.domains) },
    { key: "role", choices: named(session.job_roles) },
    { key: "level", choices: named(LEVELS) },
    { key: "path", choices: whole.paths.map((path) => ({ value: path.slug, words: path.title })) },
    { key: "status", choices: STATUSES.map((status) => ({ value: status, words: statusWords(status) })) },
  ];
  const route = (): GuideFilters => ({ ...filters, search: (filters.search ?? "").trim() });

  const draw = (announce: boolean) => {
    const narrowed = narrowListing(scoped, filters);
    pathList.replaceChildren(...narrowed.paths.flatMap((path) => pathCards.get(path.slug) ?? []));
    guideList.replaceChildren(...narrowed.guides.flatMap((guide) => guideRows.get(guide.slug) ?? []));
    pathList.hidden = narrowed.paths.length === 0;
    guideList.hidden = narrowed.guides.length === 0;
    noPaths.hidden = !pathList.hidden;
    noGuides.hidden = !guideList.hidden;
    noPaths.textContent = noMatch("paths", filters, titles);
    noGuides.textContent = noMatch("guides", filters, titles);
    const tally = countWords(narrowed, whole);
    const profile = profileChip(profileCounts(wide, scoped, filters), narrowedBy(scoped.profile));
    bar.show({ filters, count: tally, profile });
    shell.setStatus({ mode: "GUIDES", where: bar.line.hidden ? "guides and paths" : tally });
    if (announce && !bar.line.hidden) shell.announce(`showing ${tally}`);
  };
  const change = (next: FilterValues) => {
    const before = scopeQuery(filters);
    filters = Object.fromEntries(GUIDE_FILTER_KEYS.flatMap((key) => (next[key] ? [[key, next[key]]] : []))) as GuideFilters;
    history.replaceState(null, "", guidesHash(route()));
    shell.setCommand(learnCommand(route()));
    if (scopeQuery(filters) === before) {
      draw(true);
      return;
    }
    // The rows follow the labels and the widening once the server has narrowed them.
    draw(false);
    const token = ++reading;
    Promise.all([read(scopeQuery(filters)), read(wideScopeQuery(filters))])
      .then(([scopedNow, wideNow]) => {
        if (token !== reading) return;
        scoped = scopedNow;
        wide = wideNow;
        draw(true);
      })
      .catch((error: unknown) => shell.announce(`could not read the guides: ${messageOf(error)}`));
  };
  const bar = filterBar({
    name: "guides and paths",
    search: { placeholder: "search guides and paths…", label: "Search guides and paths by title, summary or slug" },
    filters,
    keys: GUIDE_FILTER_KEYS,
    row: lists,
    narrowing: sessionNarrowing(session),
    widens: LABEL_DIMENSIONS,
    describe: describeGuideFilter(titles),
    change,
    searched: (text) => change({ ...filters, search: text }),
    clearHref: GUIDES_HASH,
  });
  draw(true);

  return {
    nodes: [
      bar.row,
      bar.line,
      h(
        "section",
        { class: "guide-section", "aria-labelledby": "paths-heading" },
        h("h2", { id: "paths-heading" }, "paths"),
        h("p", { class: "quiet" }, "A path puts guides and problems in order, from a topic's first idea to an expert's. The paths run from introductory to advanced."),
        ...(whole.paths.length ? [pathList, noPaths] : [empty("no paths yet")]),
      ),
      h("section", { class: "guide-section", "aria-labelledby": "all-guides-heading" }, h("h2", { id: "all-guides-heading" }, "all guides"), guideList, noGuides),
    ],
    detach: bar.attach(),
  };
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
      h("p", { class: "guides-intro" }, "Short readings that teach an idea before you practice it, with examples and diagrams. Follow a path, or open any guide."),
      body,
    ),
  );
  let left = false;
  let detach: Cleanup = () => undefined;
  // Each listing is read once, whichever view of it asks.
  const reads = new Map<string, Promise<GuideListing>>();
  const read: Read = (query) => {
    const held = reads.get(query) ?? api.get<GuideListing>(`${GUIDES_API}${query}`);
    reads.set(query, held);
    return held;
  };
  void Promise.all([read(WHOLE_QUERY), read(scopeQuery(filters)), read(wideScopeQuery(filters))])
    .then(([whole, scoped, wide]) => {
      if (left) return;
      const drawn = listing(context, { whole, scoped, wide }, filters, read);
      detach = drawn.detach;
      body.replaceChildren(...drawn.nodes);
    })
    .catch((error: unknown) => {
      if (!left) showFailure(body, error);
    });
  return () => {
    left = true;
    detach();
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

function practice(problems: readonly string[]): HTMLElement | null {
  if (problems.length === 0) return null;
  return h(
    "section",
    { class: "side-block", "aria-labelledby": "practice-heading" },
    h("h2", { id: "practice-heading", class: "eyebrow" }, "practice"),
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
  void Promise.all([api.get<GuideDocument>(`${GUIDES_API}/${encodeURIComponent(slug)}`), api.get<GuideListing>(`${GUIDES_API}${WHOLE_QUERY}`)])
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
            practice(guide.problems),
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
  const action = step.kind === "guide" ? (step.done ? "Read again" : "Read") : step.done ? "Practice again" : "Start";
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

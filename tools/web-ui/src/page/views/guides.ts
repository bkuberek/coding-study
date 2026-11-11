/**
 * The Guides view (docs/specs/web-ui.md#guides-view), the recommended way to learn: the paths with
 * their progress and the guides with their read state (`cstudy learn`), a guide to read with its
 * diagrams drawn and a control that marks it read (`cstudy learn <guide>`, `--done`), and a path's
 * steps in order, each done or not, with a link to read the guide or start the problem
 * (`cstudy learn --path <path>`).
 */

import "./guides.css";

import type { Cleanup, PageContext } from "../context.ts";
import { command, h, rendered } from "../dom.ts";
import { diagramTheme, type DiagramTheme, progressText, stepCommand, stepHref, stepTarget } from "../guides-model.ts";
import { GUIDES_HASH, guideHash, pathHash, problemHash } from "../routes.ts";
import { empty, loading, messageOf, showFailure } from "../states.ts";
import type { GuideDocument, GuideEntry, GuideListing, MarkedRead, PathDocument, PathStep, PathSummary } from "../types.ts";

const GUIDES_API = "/api/v1/guides";
const DARK_SCHEME = "(prefers-color-scheme: dark)";
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

function listing(found: GuideListing): HTMLElement[] {
  if (found.guides.length === 0 && found.paths.length === 0) {
    return [empty("There are no guides in this content root yet.", h("p", { class: "quiet" }, command("cstudy learn")))];
  }
  return [
    h(
      "section",
      { class: "guide-section", "aria-labelledby": "paths-heading" },
      h("h2", { id: "paths-heading" }, "paths"),
      h("p", { class: "quiet" }, "A path puts guides and problems in order, from a topic's first idea to an expert's."),
      found.paths.length ? h("ul", { class: "plain path-cards" }, ...found.paths.map(pathCard)) : empty("no paths yet"),
    ),
    h(
      "section",
      { class: "guide-section", "aria-labelledby": "all-guides-heading" },
      h("h2", { id: "all-guides-heading" }, "all guides"),
      h("ul", { class: "plain guide-list" }, ...found.guides.map(guideRow)),
    ),
  ];
}

export function guidesView(context: PageContext): Cleanup {
  const { api, shell } = context;
  shell.setView("guides");
  shell.setCommand("cstudy learn");
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
      if (!left) body.replaceChildren(...listing(found));
    })
    .catch((error: unknown) => {
      if (!left) showFailure(body, error);
    });
  return () => {
    left = true;
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

/** Draws the guide's diagrams in the page's theme, and again when the theme changes. */
function followTheme(context: PageContext, body: HTMLElement): Cleanup {
  const figures = [...body.querySelectorAll<HTMLElement>("figure.diagram")];
  if (figures.length === 0) return () => {};
  for (const figure of figures) figure.setAttribute("aria-busy", "true");
  const system = window.matchMedia(DARK_SCHEME);
  const draw = () => {
    const theme: DiagramTheme = diagramTheme(context.preferences().theme, system.matches);
    import("../diagrams.ts")
      .then((diagrams) => diagrams.drawDiagrams(figures, theme, context.nonce))
      .catch((error: unknown) => context.shell.announce(`could not draw the diagrams: ${messageOf(error)}`));
  };
  draw();
  system.addEventListener("change", draw);
  const stop = context.onPreferences(draw);
  return () => {
    system.removeEventListener("change", draw);
    stop();
  };
}

export function guideView(context: PageContext, slug: string): Cleanup {
  const { api, shell } = context;
  shell.setView("guides");
  shell.setCommand(`cstudy learn ${slug}`);
  shell.setStatus({ mode: "GUIDE", where: slug });
  const page = h("article", { class: "guide", "aria-busy": "true" }, loading());
  shell.main.replaceChildren(page);
  let left = false;
  let cleanup: Cleanup = () => {};
  void Promise.all([api.get<GuideDocument>(`${GUIDES_API}/${encodeURIComponent(slug)}`), api.get<GuideListing>(GUIDES_API)])
    .then(([guide, found]) => {
      if (left) return;
      const titles = new Map(found.guides.map((entry) => [entry.slug, entry]));
      const mark = readMark(guide.read_at !== null);
      const body = rendered(guide.html, "prose guide-body");
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
      cleanup = followTheme(context, body);
    })
    .catch((error: unknown) => {
      if (!left) showFailure(page, error);
    });
  return () => {
    left = true;
    cleanup();
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

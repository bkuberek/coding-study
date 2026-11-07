/**
 * The Sets view (docs/specs/web-ui.md#sets-view): the sets of `cstudy set list` with passed of
 * total, and one set open: its `cstudy next --set` pick and its rows in order, to start, resume,
 * reorder or remove.
 */

import "./sets.css";

import { confirmed } from "../confirmation.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { badge, h } from "../dom.ts";
import { problemBadge } from "../format.ts";
import { attemptHash, problemHash, problemsHash, setHash, SETS_HASH } from "../routes.ts";
import { movesOf, setNameIssue, standingWords } from "../sets-model.ts";
import { askNames, confirmAction, openStartDialog } from "../sheets.ts";
import { empty, failure, loading, messageOf, showFailure } from "../states.ts";
import type { ListEntry, NextPick, ProblemDocument, SetDocument, SetList, SetRow, SetStanding, SetSummary } from "../types.ts";
import { nextPick } from "./problems.ts";

const SETS = "/api/v1/sets";

function setPath(name: string): string {
  return `${SETS}/${encodeURIComponent(name)}`;
}

export function setsView(context: PageContext): Cleanup {
  const { api, shell } = context;
  shell.setView("sets");
  shell.setCommand("cstudy set list");
  shell.setStatus({ mode: "SETS", where: "sets.yaml" });
  const region = h("div", { "aria-busy": "true" }, loading());
  const create = h("button", { type: "button", class: "button primary", title: "cstudy set create" }, "New set…");
  create.addEventListener("click", () => void askNewSet(context));
  shell.main.replaceChildren(
    h(
      "section",
      { class: "sets", "aria-labelledby": "sets-heading" },
      h("header", { class: "view-head" }, h("h1", { id: "sets-heading" }, "sets"), create),
      h("p", { class: "quiet" }, "Lists you chose, in the order you study them. They live in sets.yaml in your workspace, and a reset keeps them."),
      region,
    ),
  );
  api
    .get<SetList>(SETS)
    .then(({ sets }) => {
      region.removeAttribute("aria-busy");
      region.replaceChildren(
        sets.length ? setList(sets) : empty("no sets yet", h("p", { class: "quiet" }, "Make one for what is coming up, then add problems from the Problems view.")),
      );
    })
    .catch((error: unknown) => {
      region.removeAttribute("aria-busy");
      showFailure(region, error);
      create.disabled = true;
    });
  return () => {};
}

function progressBar(standing: SetStanding): HTMLElement {
  return h("progress", { class: "set-progress", value: standing.passed, max: Math.max(standing.total, 1), "aria-label": standingWords(standing) });
}

function setList(sets: readonly SetSummary[]): HTMLElement {
  return h(
    "ul",
    { class: "set-list" },
    ...sets.map((found) =>
      h(
        "li",
        {},
        h("a", { href: setHash(found.name), class: "set-name" }, found.name),
        h("span", { class: "quiet" }, found.description ?? ""),
        progressBar(found),
        h("span", { class: "num" }, standingWords(found)),
      ),
    ),
  );
}

async function askNewSet(context: PageContext): Promise<void> {
  await askNames({
    title: "new set",
    note: "As cstudy set create. A problem can be in several sets.",
    action: "Create",
    fields: [
      { label: "Name", prefix: "", value: "", issue: setNameIssue },
      { label: "Description (optional)", prefix: "", value: "", issue: () => null },
    ],
    submit: async ([name = "", description = ""]) => {
      await context.api.post(SETS, { name, description: description || null });
      location.hash = setHash(name);
      return null;
    },
  });
}

/** Where the focus goes once the rows are drawn again: a control of a row, else the add field. */
interface FocusAfter {
  readonly slug: string;
  readonly actions: readonly string[];
}

export function setView(context: PageContext, name: string): Cleanup {
  const { api, shell } = context;
  shell.setView("sets");
  shell.setCommand(`cstudy set show ${name}`);
  shell.setStatus({ mode: "SET", where: name });
  const page = h("article", { class: "set-open", "aria-busy": "true" }, loading());
  shell.main.replaceChildren(page);
  let current = name;

  const load = (focus?: FocusAfter | "add"): void => {
    const path = setPath(current);
    Promise.allSettled([api.get<SetDocument>(path), api.get<NextPick>(`/api/v1/next?set=${encodeURIComponent(current)}`)])
      .then(([found, pick]) => {
        page.removeAttribute("aria-busy");
        if (found.status === "rejected") {
          showFailure(page, found.reason);
          return;
        }
        page.replaceChildren(...opened(found.value, pick));
        shell.setStatus({ mode: "SET", where: `${current} · ${standingWords(found.value)}` });
        if (focus !== undefined) restoreFocus(focus);
      })
      .catch((error: unknown) => showFailure(page, error));
  };

  const restoreFocus = (focus: FocusAfter | "add"): void => {
    const field = page.querySelector<HTMLElement>("#set-add-slug");
    if (focus === "add") {
      field?.focus();
      return;
    }
    const usable = focus.actions
      .map((action) => page.querySelector<HTMLButtonElement>(`button[data-slug="${CSS.escape(focus.slug)}"][data-action="${action}"]:not(:disabled)`))
      .find((found) => found !== null);
    (usable ?? field)?.focus();
  };

  const change = (run: () => Promise<unknown>, said: string, focus: FocusAfter | "add"): void => {
    run()
      .then(() => {
        shell.announce(said);
        load(focus);
      })
      .catch((error: unknown) => showFailure(page, error));
  };

  const opened = (found: SetDocument, pick: PromiseSettledResult<NextPick>): Node[] => [
    head(found),
    pickSection(found, pick),
    found.rows.length ? rowsTable(found) : empty("nothing in this set yet", h("p", { class: "quiet" }, "Add a problem below, or from a row of the Problems view.")),
    addForm(found),
  ];

  const head = (found: SetDocument): HTMLElement => {
    const rename = h("button", { type: "button", class: "button", title: `cstudy set rename ${found.name} <new-name>` }, "Rename…");
    const remove = h("button", { type: "button", class: "button", title: `cstudy set delete ${found.name}` }, "Delete…");
    rename.addEventListener("click", () => void askRename(found.name));
    remove.addEventListener("click", () => void askDelete(found.name));
    return h(
      "header",
      {},
      h("p", { class: "eyebrow set-crumb" }, h("a", { href: SETS_HASH }, "sets")),
      h("div", { class: "view-head" }, h("h1", {}, found.name), h("div", { class: "set-actions" }, rename, remove)),
      found.description ? h("p", {}, found.description) : null,
      h(
        "p",
        { class: "set-facts" },
        progressBar(found),
        h("span", { class: "num" }, standingWords(found)),
        h("a", { href: problemsHash({ set: found.name }) }, "filter the Problems view by this set"),
      ),
    );
  };

  const pickSection = (found: SetDocument, pick: PromiseSettledResult<NextPick>): HTMLElement => {
    const card = h("section", { class: "next-card", "aria-labelledby": "set-next-heading" }, h("h2", { id: "set-next-heading", class: "eyebrow" }, "next"));
    if (pick.status === "rejected") card.append(failure(pick.reason));
    else card.append(...nextPick(pick.value, { set: found.name }));
    return card;
  };

  const rowsTable = (found: SetDocument): HTMLElement =>
    h(
      "section",
      { class: "listing table-scroll", "aria-label": `The rows of ${found.name}`, tabindex: "0" },
      h(
        "table",
        { class: "problems set-table" },
        h("caption", { class: "sr-only" }, `The rows of ${found.name}, in its order`),
        h("thead", {}, h("tr", {}, ...["#", "problem", "diff", "status", "practise", "order"].map((title) => h("th", { scope: "col" }, title)))),
        h("tbody", {}, ...found.rows.map((row) => rowOf(found, row))),
      ),
    );

  const rowOf = (found: SetDocument, row: SetRow): HTMLTableRowElement => {
    const entry = row.entry;
    const status = entry === null ? { glyph: "?", text: "missing", tone: "warn" } : problemBadge(entry.status);
    return h(
      "tr",
      { class: entry?.kind === "item" ? "is-item" : null },
      h("td", { class: "num" }, row.position),
      entry === null
        ? h("td", { class: "title-cell" }, h("span", { class: "slug" }, row.slug))
        : h("td", { class: "title-cell" }, h("a", { href: problemHash(entry.slug), class: "slug" }, entry.slug), h("span", { class: "title" }, entry.title)),
      entry === null ? h("td", {}, "–") : h("td", { class: `diff diff-${entry.difficulty}` }, entry.difficulty),
      h("td", {}, badge(status.glyph, status.text, status.tone)),
      h("td", { class: "resume" }, ...(entry === null ? [] : practise(entry))),
      h("td", { class: "set-order" }, ...orderControls(found, row)),
    );
  };

  const practise = (entry: ListEntry): Node[] =>
    entry.in_progress.length
      ? entry.in_progress.map((attempt) => h("a", { href: attemptHash(attempt.attempt_id), class: "resume-link", title: `Resume attempt ${attempt.attempt_id}` }, `Resume ${attempt.language ?? "notes"}`))
      : [startButton(entry)];

  const startButton = (entry: ListEntry): HTMLElement => {
    const start = h("button", { type: "button", class: "button", title: `cstudy start ${entry.slug}`, "aria-label": `Start ${entry.slug}` }, "Start…");
    start.addEventListener("click", () => {
      start.disabled = true;
      api
        .get<ProblemDocument>(`/api/v1/problems/${encodeURIComponent(entry.slug)}`)
        .then((problem) => openStartDialog(context, problem, entry.due_on !== null))
        .catch((error: unknown) => start.replaceWith(failure(error)))
        .finally(() => {
          start.disabled = false;
        });
    });
    return start;
  };

  const orderControls = (found: SetDocument, row: SetRow): HTMLElement[] => {
    const moves = movesOf(row.position, found.rows.length);
    const path = setPath(found.name);
    const moveButton = (action: "up" | "down", label: string, position: number | null): HTMLElement => {
      const button = h(
        "button",
        {
          type: "button",
          class: "ghost",
          disabled: position === null,
          "data-slug": row.slug,
          "data-action": action,
          "aria-label": `Move ${row.slug} ${action}`,
          title: position === null ? `${row.slug} is at the ${action === "up" ? "top" : "bottom"}` : `cstudy set move ${found.name} ${row.slug} ${position}`,
        },
        label,
      );
      button.addEventListener("click", () => {
        if (position === null) return;
        const body = { slug: row.slug, position };
        change(() => api.post(`${path}/move`, body), `moved ${row.slug} to ${position}`, { slug: row.slug, actions: [action, action === "up" ? "down" : "up"] });
      });
      return button;
    };
    const remove = h(
      "button",
      { type: "button", class: "ghost", "data-slug": row.slug, "data-action": "remove", "aria-label": `Remove ${row.slug}`, title: `cstudy set remove ${found.name} ${row.slug}` },
      "Remove",
    );
    remove.addEventListener("click", () => {
      const following = found.rows[row.position]?.slug ?? found.rows[row.position - 2]?.slug;
      const focus = following === undefined ? "add" : { slug: following, actions: ["remove"] };
      change(() => api.post(`${path}/remove`, { slugs: [row.slug] }), `removed ${row.slug}`, focus);
    });
    return [moveButton("up", "Up", moves.up), moveButton("down", "Down", moves.down), remove];
  };

  const addForm = (found: SetDocument): HTMLElement => {
    const field = h("input", { id: "set-add-slug", type: "text", spellcheck: "false", autocomplete: "off", autocapitalize: "off", placeholder: "two-sum", "aria-describedby": "set-add-issue" });
    const issue = h("p", { id: "set-add-issue", class: "set-issue", "aria-live": "polite" });
    const form = h(
      "form",
      { class: "set-add", novalidate: true },
      h("label", { for: field.id }, "Add a problem or item by slug"),
      field,
      h("button", { type: "submit", class: "button", title: `cstudy set add ${found.name} <slug>` }, "Add"),
      issue,
      h("p", { class: "quiet" }, "Or add from a row of ", h("a", { href: "#/" }, "the Problems view"), "."),
    );
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const slug = field.value.trim();
      if (slug === "") return;
      issue.textContent = "";
      api
        .post<{ readonly already: readonly string[] }>(`${setPath(found.name)}/add`, { slugs: [slug] })
        .then(({ already }) => {
          shell.announce(already.length ? `${slug} is already in ${found.name}` : `added ${slug} to ${found.name}`);
          load("add");
        })
        .catch((error: unknown) => {
          issue.textContent = messageOf(error);
          field.focus();
        });
    });
    return form;
  };

  const askRename = async (old: string): Promise<void> => {
    await askNames({
      title: `rename ${old}`,
      note: `As cstudy set rename ${old} <new-name>. Its rows stay.`,
      action: "Rename",
      fields: [{ label: "New name", prefix: "", value: old, issue: setNameIssue }],
      submit: async ([renamed = old]) => {
        await api.post(`${setPath(old)}/rename`, { to: renamed });
        current = renamed;
        location.hash = setHash(renamed);
        return null;
      },
    });
  };

  const askDelete = async (old: string): Promise<void> => {
    const path = setPath(old);
    const done = await confirmed(
      (confirm) => api.send<{ readonly deleted: string }>("DELETE", path, { body: { confirm } }),
      (question) => confirmAction({ title: `delete ${old}`, message: question, action: "Delete", destructive: true, command: `cstudy set delete ${old}` }),
    ).catch((error: unknown) => {
      showFailure(page, error);
      return null;
    });
    if (done) location.hash = SETS_HASH;
  };

  load();
  return () => {};
}

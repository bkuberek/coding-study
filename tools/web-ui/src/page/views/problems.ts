/**
 * The Problems view (docs/specs/web-ui.md#problems-view): the `cstudy next` pick with its action, the
 * search and the filters of `cstudy list`, kept in the fragment's query, the chips of what is active,
 * and the table in the columns the preferences hold, items after problems.
 */

import "./problems.css";

import { listCommand, nextCommand, NEXT_FILTERS, startCommand } from "../commands.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { badge, type Child, command, h, isTyping } from "../dom.ts";
import { problemBadge } from "../format.ts";
import { jdkRefusals, type SelectedJdk } from "../jdk.ts";
import {
  activeFilters,
  canHide,
  choiceWords,
  counted,
  countWords,
  DEFAULT_COLUMNS,
  matchesSearch,
  PROBLEM_COLUMNS,
  type ProblemColumn,
  shownColumns,
  withColumn,
} from "../problems-model.ts";
import { attemptHash, FILTER_KEYS, type FilterKey, type Filters, problemHash, problemsHash } from "../routes.ts";
import { setControl, setsHolding } from "../setControl.ts";
import { empty, failure, loading, messageOf, showFailure } from "../states.ts";
import type { AttemptRef, ListEntry, NextPick, ProblemDocument, ProblemList, SetList, SetSummary } from "../types.ts";

const DIFFICULTIES = ["easy", "medium", "hard"];
const STATUSES = ["new", "in_progress", "attempted", "passed", "due", "mastered"];
const CONTENT = ["draft", "ready"];
/** The filters the server answers; the search narrows the rows already here. */
const LIST_FILTERS = FILTER_KEYS.filter((key) => key !== "search");
const ROW_FILTERS = ["status", "difficulty", "domain", "lang"] as const;
const MORE_FILTERS = ["track", "kind", "role", "scope", "pattern", "content", "set"] as const;
const SEARCH_FIELD = "filter-search";
type ChoiceKey = Exclude<FilterKey, "search">;
type Picked = Exclude<NextPick, { readonly pick: null }>;
const LANGUAGE_LABELS: Readonly<Record<string, string>> = {
  python: "py",
  typescript: "ts",
  java: "java",
  kotlin: "kt",
  go: "go",
  rust: "rs",
};

/** The field to focus once a change of the filters has drawn the view again. */
let focusAfterDraw: string | null = null;

export function problemsView(context: PageContext, filters: Filters): Cleanup {
  const { api, shell, session } = context;
  shell.setView("problems");
  shell.setCommand(listCommand(filters));
  shell.setStatus({ mode: "LIST", where: "problems" });

  const next = h("section", { class: "next-card", "aria-labelledby": "next-heading" });
  // Focusable, so the keyboard scrolls the table where a narrow window gives it a box of its own.
  const table = h("section", { class: "listing table-scroll", "aria-label": "Problems", "aria-busy": "true", tabindex: "0" }, loading());
  const choices: Readonly<Record<ChoiceKey, readonly string[]>> = {
    set: [],
    track: session.tracks,
    kind: session.kinds,
    lang: session.languages,
    difficulty: DIFFICULTIES,
    status: STATUSES,
    content: CONTENT,
    domain: session.domains,
    role: session.job_roles,
    scope: session.scopes,
    pattern: session.patterns,
  };
  let searched = filters.search ?? "";
  const route = (): Filters => ({ ...filters, search: searched.trim() });
  const count = h("span", { class: "filter-count" });
  const summary = filterSummary(route, count);
  let narrow: () => void = () => {};
  let drawRows: () => void = () => {};
  const showRoute = () => {
    summary.hidden = activeFilters(route()).length === 0 && !route().search;
    shell.setCommand(listCommand(route()));
  };
  const form = filterForm(route, choices, (text) => {
    searched = text;
    history.replaceState(null, "", problemsHash(route()));
    showRoute();
    narrow();
  });
  showRoute();
  shell.main.replaceChildren(
    h("h1", { class: "sr-only" }, "Problems"),
    next,
    h("div", { class: "filter-bar" }, form, columnsMenu(context, () => drawRows())),
    summary,
    table,
  );
  const nextHeading = () => h("h2", { id: "next-heading", class: "sr-only" }, "next");
  next.replaceChildren(nextHeading(), loading("picking…"));
  takeTheFocus(shell.main);

  // The pick and the table show together: the pick changes the height of the card above the
  // table, so a table drawn first would move under a pointer about to click a row.
  const load = () =>
    void Promise.allSettled([
      api.get<ProblemList>(`/api/v1/problems${queryOf(filters, LIST_FILTERS)}`),
      api.get<NextPick>(`/api/v1/next${queryOf(filters, NEXT_FILTERS)}`),
      api.get<SetList>("/api/v1/sets"),
      // What the count is out of, and the attempts in progress whatever the filters leave out.
      LIST_FILTERS.some((key) => filters[key]) ? api.get<ProblemList>("/api/v1/problems") : undefined,
    ]).then(([list, pick, sets, whole]) => {
      if (pick.status === "fulfilled") next.replaceChildren(nextHeading(), ...nextPick(context, pick.value, filters));
      else showFailure(next, pick.reason);
      const known = sets.status === "fulfilled" ? sets.value.sets : [];
      fillSetChoices(form, known);
      const brokenSets = sets.status === "rejected" ? [failure(sets.reason)] : [];
      const everything = whole.status === "rejected" ? null : (whole.value ?? (list.status === "fulfilled" ? list.value : null));
      if (everything !== null) shell.setAttempts(everything.entries);
      if (list.status === "rejected") {
        showFailure(table, list.reason);
        return;
      }
      const { entries, today, selected_jdk: selectedJdk, set: inSet } = list.value;
      table.removeAttribute("aria-busy");
      const changedSets = new Map<string, readonly string[]>();
      const drawing: RowDrawing = {
        selectedJdk,
        // Unticking the set a row is listed under takes the row out, once its dialog closes.
        setsOf: (slug) =>
          setControl(context, slug, {
            held: changedSets.get(slug) ?? setsHolding(known, slug),
            closed: (names) => {
              changedSets.set(slug, names);
              if (filters.set && !names.includes(filters.set)) {
                load();
                table.focus({ preventScroll: true });
              }
            },
          }),
      };
      drawRows = () => {
        const columns = shownColumns(context.preferences().problem_columns);
        const rows = listing(entries, columns, drawing);
        table.classList.toggle("has-more-columns", columns.length > DEFAULT_COLUMNS.length);
        table.replaceChildren(
          ...brokenSets,
          ...(inSet?.missing.length ? [h("p", { class: "quiet" }, `missing from the catalog: ${inSet.missing.join(", ")}`)] : []),
          ...rows.nodes,
        );
        narrow = () => {
          const found = rows.narrow(searched);
          const items = found.filter((entry) => entry.kind === "item").length;
          shell.setStatus({ mode: "LIST", where: `${counted(found.length - items, "problem")} · ${counted(items, "item")} · ${today}` });
          count.textContent = countWords(found.length, everything?.entries.length ?? null);
          if (!summary.hidden) shell.announce(`showing ${count.textContent}`);
        };
        narrow();
      };
      drawRows();
    });
  load();
  const focusSearch = (event: KeyboardEvent) => {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target) || document.querySelector("dialog[open]")) return;
    event.preventDefault();
    form.querySelector<HTMLInputElement>("#filter-search")?.focus();
  };
  const closeMenus = (event: MouseEvent) => {
    for (const menu of shell.main.querySelectorAll<HTMLDetailsElement>(".filter-menu[open]")) {
      if (!menu.contains(event.target as Node)) menu.open = false;
    }
  };
  document.addEventListener("keydown", focusSearch);
  document.addEventListener("click", closeMenus);
  return () => {
    document.removeEventListener("keydown", focusSearch);
    document.removeEventListener("click", closeMenus);
  };
}

/** The sets arrive after the form is drawn, and again each time the list reads again; the filter
 * lists what it does not hold yet, so it keeps what the route names and lists each set once. */
function fillSetChoices(form: HTMLFormElement, sets: readonly SetSummary[]): void {
  const select = form.querySelector<HTMLSelectElement>("#filter-set");
  if (select === null) return;
  const listed = new Set([...select.options].map((option) => option.value));
  const names = sets.map((found) => found.name).filter((name) => !listed.has(name));
  select.append(...names.map((value) => h("option", { value }, value)));
}

function queryOf(filters: Filters, keys: readonly FilterKey[]): string {
  const query = new URLSearchParams();
  for (const key of keys) {
    const value = filters[key];
    if (value) query.set(key, value);
  }
  const text = query.toString();
  return text ? `?${text}` : "";
}

/** What the Next panel does with a pick: a resume opens its attempt, and a start opens the dialog
 * every Start control opens, in the dialogs' chunk. */
function nextAction(context: PageContext, pick: Picked): HTMLElement {
  const line = startCommand(pick.slug, pick.language);
  if (pick.attempt_id !== undefined) return h("a", { href: attemptHash(pick.attempt_id), class: "button primary next-action", title: line }, "Resume");
  const start = h("button", { type: "button", class: "button primary next-action", title: `${line} --no-open` }, "Start…");
  let opening = false;
  start.addEventListener("click", () => {
    if (opening) return;
    opening = true;
    // The dialog gives the focus back to what had it, and a click leaves it elsewhere in some browsers.
    start.focus();
    Promise.all([context.api.get<ProblemDocument>(`/api/v1/problems/${encodeURIComponent(pick.slug)}`), import("../sheets.ts")])
      .then(([problem, sheets]) => sheets.openStartDialog(context, problem, pick.pick === "review"))
      .catch((error: unknown) => start.replaceWith(failure(error)))
      .finally(() => {
        opening = false;
      });
  });
  return start;
}

/** The pick and its action, two lines tall: what it is and why, then its command in small text, and
 * the other attempts in progress, to pick another. */
export function nextPick(context: PageContext, pick: NextPick, filters: Filters): Node[] {
  if (pick.pick === null) return [h("p", { class: "next-line" }, pick.message)];
  return [
    nextAction(context, pick),
    h(
      "div",
      { class: "next-body" },
      h(
        "p",
        { class: "next-line" },
        h("span", { class: `pick pick-${pick.pick}` }, pick.pick),
        h("a", { href: pick.attempt_id === undefined ? problemHash(pick.slug) : attemptHash(pick.attempt_id), class: "next-slug" }, pick.slug),
        h("span", { class: "quiet" }, `(${pick.difficulty} · ${pick.group})`),
        h("span", { class: "next-reason" }, pick.reason),
      ),
      h(
        "div",
        { class: "next-foot" },
        h("p", { class: "next-start" }, command(startCommand(pick.slug, pick.language)), h("span", { class: "quiet next-same" }, ` · same as ${nextCommand(filters)}`)),
        pick.also_open?.length
          ? h(
              "p",
              { class: "next-also" },
              h("span", { class: "quiet" }, "or pick up "),
              ...pick.also_open.map((other) => h("a", { href: attemptHash(other.attempt_id), class: "resume-link" }, `↻ ${other.slug}${other.language ? ` (${other.language})` : ""}`)),
            )
          : null,
      ),
    ),
  ];
}

/** A filter's list; the value the route names stays a choice, whatever the list holds. */
function filterSelect(key: ChoiceKey, chosen: string | undefined, choices: readonly string[], blank: string, apply: (key: FilterKey, value: string) => void): HTMLSelectElement {
  const values = chosen && !choices.includes(chosen) ? [chosen, ...choices] : choices;
  const select = h(
    "select",
    { id: `filter-${key}`, name: key, class: chosen ? "is-set" : null },
    h("option", { value: "" }, blank),
    ...values.map((value) => h("option", { value, selected: chosen === value }, choiceWords(key, value))),
  );
  select.addEventListener("change", () => {
    focusAfterDraw = select.id;
    apply(key, select.value);
  });
  return select;
}

/** A menu that a click elsewhere (`closeMenus`), Escape and tabbing out of it close. */
function filterMenu(name: string, label: readonly Child[], ...content: Child[]): HTMLDetailsElement {
  const summary = h("summary", {}, ...label);
  const menu = h("details", { class: `filter-menu ${name}` }, summary, h("div", { class: "filter-panel" }, ...content));
  menu.addEventListener("keydown", (event) => {
    if (event.key === "Tab") {
      window.setTimeout(() => {
        if (!menu.contains(document.activeElement)) menu.open = false;
      });
    } else if (event.key === "Escape" && menu.open) {
      event.preventDefault();
      menu.open = false;
      summary.focus();
    }
  });
  return menu;
}

/** The slim row: the search, the filters used most, and More for the others. */
function filterForm(route: () => Filters, choices: Readonly<Record<ChoiceKey, readonly string[]>>, searched: (text: string) => void): HTMLFormElement {
  const filters = route();
  const apply = (key: FilterKey, value: string) => {
    location.hash = problemsHash({ ...route(), [key]: value });
  };
  const search = h("input", {
    id: "filter-search",
    name: "search",
    type: "search",
    value: filters.search ?? "",
    placeholder: "search problems…",
    spellcheck: "false",
    autocomplete: "off",
    "aria-keyshortcuts": "/",
  });
  search.addEventListener("input", () => searched(search.value));
  const inMore = MORE_FILTERS.filter((key) => filters[key]).length;
  const form = h(
    "form",
    { class: "filters", role: "search", "aria-label": "Filter problems" },
    h("label", { class: "filter-search", for: search.id }, h("span", { class: "sr-only" }, "Search problems by title or slug"), h("span", { class: "filter-prompt", "aria-hidden": "true" }, ">"), search),
    ...ROW_FILTERS.map((key) =>
      h("label", { class: "filter", for: `filter-${key}` }, h("span", { class: "sr-only" }, key), filterSelect(key, filters[key], choices[key], key, apply)),
    ),
    filterMenu(
      "filter-more",
      ["more", inMore ? h("span", { class: "filter-more-count" }, inMore, h("span", { class: "sr-only" }, " active")) : null],
      ...MORE_FILTERS.map((key) =>
        h("label", { class: "filter-field", for: `filter-${key}` }, h("span", { class: "filter-name" }, key), filterSelect(key, filters[key], choices[key], "any", apply)),
      ),
    ),
  );
  form.addEventListener("submit", (event) => event.preventDefault());
  return form;
}

/** What the filters leave: a chip per filter, the count and Clear. It takes no space with none. */
function filterSummary(route: () => Filters, count: HTMLElement): HTMLElement {
  const active = activeFilters(route());
  const chips = active.map(({ key, words }, index) => {
    const chip = h("button", { type: "button", id: `chip-${key}`, class: "filter-chip", "aria-label": `Remove the filter ${words}` }, words, " ", h("span", { "aria-hidden": "true" }, "×"));
    const neighbour = active[index + 1] ?? active[index - 1];
    chip.addEventListener("click", () => {
      focusAfterDraw = neighbour === undefined ? SEARCH_FIELD : `chip-${neighbour.key}`;
      location.hash = problemsHash({ ...route(), [key]: "" });
    });
    return chip;
  });
  const clear = h("a", { href: "#/", class: "clear" }, "clear");
  clear.addEventListener("click", () => {
    focusAfterDraw = SEARCH_FIELD;
  });
  return h("div", { class: "filter-summary" }, ...chips, h("span", { class: "filter-tally" }, count, h("span", { class: "quiet" }, " · "), clear));
}

/** Gives the field a change left the focus on, in the form the change drew again. */
function takeTheFocus(root: HTMLElement): void {
  const target = focusAfterDraw === null ? null : root.querySelector<HTMLElement>(`#${focusAfterDraw}`);
  focusAfterDraw = null;
  target?.closest("details")?.setAttribute("open", "");
  target?.focus({ preventScroll: true });
}

/** A menu of the table's columns, each change stored in the preferences at once. */
function columnsMenu(context: PageContext, changed: () => void): HTMLDetailsElement {
  const boxes = PROBLEM_COLUMNS.map((column) => {
    const box = h("input", { type: "checkbox", id: `column-${column}`, value: column, disabled: !canHide(column), title: canHide(column) ? null : "always shown" });
    box.addEventListener("change", () => save(withColumn(context.preferences().problem_columns, column, box.checked)));
    return box;
  });
  const tick = () => {
    const shown = shownColumns(context.preferences().problem_columns);
    for (const box of boxes) box.checked = shown.includes(box.value as ProblemColumn);
  };
  const save = (columns: readonly string[]) => {
    context
      .savePreferences({ problem_columns: columns })
      .then(changed)
      .catch((error: unknown) => context.shell.announce(`could not save the columns: ${messageOf(error)}`))
      .finally(tick);
  };
  const reset = h("button", { type: "button", class: "ghost column-reset", title: "Back to the columns the table starts with" }, "Reset to defaults");
  reset.addEventListener("click", () => save(DEFAULT_COLUMNS));
  tick();
  return filterMenu(
    "columns-menu",
    ["columns"],
    h("div", { role: "group", "aria-label": "The columns of the table" }, ...boxes.map((box) => h("label", { class: "column-choice", for: box.id }, box, " ", box.value))),
    reset,
  );
}

/** What a row needs beyond its entry. */
interface RowDrawing {
  readonly selectedJdk: SelectedJdk | null;
  readonly setsOf: (slug: string) => HTMLElement;
}

/** A click anywhere on a row is a click on its link, with its modifier keys, so Ctrl or Cmd opens a
 * tab there too. A control does what it does, a drag selects text, and a click that closes an open
 * menu does only that. */
function openRow(event: MouseEvent): void {
  const target = event.target as Element;
  if (target.closest("a, button, input, select, label, summary") || !document.getSelection()?.isCollapsed || document.querySelector(".filter-menu[open]")) return;
  target.closest("tr")?.querySelector(".problem-link")?.dispatchEvent(new MouseEvent("click", event));
}

/** The table and what it says with no row to show; `narrow` keeps the rows a search finds. */
function listing(
  entries: readonly ListEntry[],
  columns: readonly ProblemColumn[],
  drawing: RowDrawing,
): { readonly nodes: readonly HTMLElement[]; narrow(text: string): readonly ListEntry[] } {
  const rows = entries.map((entry) => ({ entry, element: row(entry, columns, drawing) }));
  const body = h("tbody");
  body.addEventListener("click", openRow);
  const table = h(
    "table",
    { class: "problems problem-rows" },
    h("caption", { class: "sr-only" }, "Problems, then items, matching the filters"),
    h("thead", {}, h("tr", {}, ...columns.map((name) => h("th", { scope: "col" }, name)))),
    body,
  );
  const none = empty("no problems match", h("a", { href: "#/" }, "clear the filters"));
  return {
    nodes: [table, none],
    narrow(text) {
      const found = rows.filter(({ entry }) => matchesSearch(entry, text));
      body.replaceChildren(...found.map(({ element }) => element));
      table.hidden = found.length === 0;
      none.hidden = found.length > 0;
      return found.map(({ entry }) => entry);
    },
  };
}

/**
 * The languages of a problem, as `cstudy list` writes them; a Java or Kotlin the selected JDK
 * cannot run ends in `!`, with the CLI's reason as the tooltip and as text for assistive technology
 * (docs/specs/web-ui.md#problems-view).
 */
function languageRefs(entry: ListEntry, selectedJdk: SelectedJdk | null): Node[] {
  if (entry.languages.length === 0) return [document.createTextNode("–")];
  const refusals = jdkRefusals(entry.slug, entry.languages, selectedJdk, entry.jdk);
  return entry.languages.flatMap((language, index) => {
    const label = LANGUAGE_LABELS[language] ?? language;
    const refusal = refusals.get(language);
    const ref =
      refusal === undefined
        ? document.createTextNode(label)
        : h(
            "span",
            { class: "ref-blocked" },
            h("span", { "aria-hidden": "true", title: refusal }, `${label}!`),
            h("span", { class: "sr-only" }, `${label}: ${refusal}`),
          );
    return index === 0 ? [ref] : [document.createTextNode(" "), ref];
  });
}

/** A link that resumes an attempt. It keeps the word it shows, `said`, in what a screen reader hears. */
function resumeLink(slug: string, attempt: AttemptRef, said: string | null, shown: Child): HTMLElement {
  const resume = `resume ${slug} in ${attempt.language ?? "notes"}`;
  return h(
    "a",
    { href: attemptHash(attempt.attempt_id), class: "resume-link", title: `Resume attempt ${attempt.attempt_id}`, "aria-label": said === null ? resume : `${said}: ${resume}` },
    shown,
  );
}

function labelsOf(labels: readonly string[]): string {
  return labels.length ? labels.join(", ") : "–";
}

/** Each column's cell of a row. */
const CELLS: Readonly<Record<ProblemColumn, (entry: ListEntry, drawing: RowDrawing) => HTMLTableCellElement>> = {
  id: (entry) => h("td", { class: "num" }, entry.id ?? "–"),
  problem: (entry) =>
    h(
      "td",
      { class: "title-cell" },
      h("a", { href: problemHash(entry.slug), class: "problem-link" }, entry.title),
      h("span", { class: "slug" }, entry.slug),
      entry.content === "draft" ? h("span", { class: "tag" }, "draft") : null,
      entry.source === "workspace" ? h("span", { class: "tag" }, "yours") : null,
    ),
  difficulty: (entry) => h("td", { class: `diff diff-${entry.difficulty}` }, entry.difficulty),
  pattern: (entry) => h("td", {}, entry.patterns[0] ?? entry.track),
  kind: (entry) => h("td", { class: "quiet" }, entry.kind),
  scope: (entry) => h("td", { class: "quiet" }, entry.scope ?? "–"),
  domain: (entry) => h("td", { class: "quiet" }, labelsOf(entry.domains)),
  role: (entry) => h("td", { class: "quiet" }, labelsOf(entry.job_roles)),
  status: (entry) => {
    const status = problemBadge(entry.status);
    const word = badge(status.glyph, status.text, status.tone);
    const [first, ...others] = entry.in_progress;
    if (first === undefined) return h("td", {}, word);
    return h("td", {}, resumeLink(entry.slug, first, status.text, word), ...others.map((attempt) => resumeLink(entry.slug, attempt, null, `↻ ${attempt.language ?? "notes"}`)));
  },
  due: (entry) => h("td", { class: "num quiet" }, entry.due_on ?? "–"),
  languages: (entry, { selectedJdk }) => h("td", { class: "refs quiet" }, ...languageRefs(entry, selectedJdk)),
  sets: (entry, { setsOf }) => h("td", {}, setsOf(entry.slug)),
};

function row(entry: ListEntry, columns: readonly ProblemColumn[], drawing: RowDrawing): HTMLTableRowElement {
  return h(
    "tr",
    { class: entry.kind === "item" ? "is-item" : null },
    ...columns.map((column) => {
      const cell = CELLS[column](entry, drawing);
      cell.dataset["column"] = column;
      return cell;
    }),
  );
}

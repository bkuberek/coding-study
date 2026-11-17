/**
 * The Problems view (docs/specs/web-ui.md#problems-view): the `cstudy next` pick with its action, the
 * search and the filters of `cstudy list` that the filter component draws, kept in the fragment's
 * query with the widening of the learner profile, the chips of what is active, and the table in the
 * columns the preferences hold, in the order of `cstudy list`.
 */

import "./problems.css";

import { listCommand, nextCommand, NEXT_FILTERS, startCommand } from "../commands.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { badge, type Child, command, h } from "../dom.ts";
import { filterBar, filterMenu, type ListFilter } from "../filter-bar.ts";
import { apiQuery, DIMENSIONS, LABEL_DIMENSIONS, narrowedBy, type ProfileChip, profileChip, sessionNarrowing, wideQuery } from "../filter-model.ts";
import { problemBadge } from "../format.ts";
import { selfGraded } from "../kinds.ts";
import { jdkRefusals, type SelectedJdk } from "../jdk.ts";
import { needMarkers } from "../needs-model.ts";
import {
  canHide,
  checkedWords,
  choiceWords,
  columnLabel,
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
const CHECKED = ["tests", "rubric", "ai-review"];
/** The filters the server answers, and the widening; the search narrows the rows already here. */
const LIST_FILTERS = FILTER_KEYS.filter((key) => key !== "search");
const ROW_FILTERS = ["status", "difficulty", "domain", "lang"] as const;
const MORE_FILTERS = ["track", "kind", "checked", "role", "scope", "pattern", "content", "set"] as const;
type ChoiceKey = Exclude<FilterKey, "search" | "widen">;
type Picked = Exclude<NextPick, { readonly pick: null }>;
const LANGUAGE_LABELS: Readonly<Record<string, string>> = {
  python: "py",
  typescript: "ts",
  java: "java",
  kotlin: "kt",
  go: "go",
  rust: "rs",
};

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
    checked: CHECKED,
    lang: session.languages,
    difficulty: DIFFICULTIES,
    status: STATUSES,
    content: CONTENT,
    domain: session.domains,
    role: session.job_roles,
    scope: session.scopes,
    pattern: session.patterns,
  };
  const listOf = (key: ChoiceKey): ListFilter => ({ key, choices: choices[key].map((value) => ({ value, words: choiceWords(key, value) })) });
  const narrowing = sessionNarrowing(session);
  let searched = filters.search ?? "";
  const route = (): Filters => ({ ...filters, search: searched.trim() });
  let tally = "";
  let profile: ProfileChip | null = null;
  let narrow: () => void = () => {};
  let drawRows: () => void = () => {};
  const bar = filterBar({
    name: "problems",
    search: { placeholder: "search problems…", label: "Search problems by title or slug" },
    filters,
    keys: FILTER_KEYS,
    row: ROW_FILTERS.map(listOf),
    more: MORE_FILTERS.map(listOf),
    narrowing,
    widens: DIMENSIONS,
    describe: choiceWords,
    // A change is the route's, replaced in place, which draws the view again from the server's rows.
    change: (changed) => location.replace(problemsHash(changed as Filters)),
    searched: (text) => {
      searched = text;
      history.replaceState(null, "", problemsHash(route()));
      showRoute();
      narrow();
    },
    beside: [columnsMenu(context, () => drawRows())],
    clearHref: "#/",
  });
  const showRoute = () => {
    shell.setCommand(listCommand(route()));
    bar.show({ filters: route(), count: tally, profile });
  };
  shell.main.replaceChildren(h("h1", { class: "sr-only" }, "Problems"), next, bar.row, bar.line, table);
  showRoute();
  const nextHeading = () => h("h2", { id: "next-heading", class: "sr-only" }, "next");
  next.replaceChildren(nextHeading(), loading("picking…"));

  // The pick and the table show together: the pick changes the height of the card above the
  // table, so a table drawn first would move under a pointer about to click a row. What the count
  // is out of, and the attempts in progress, ignore both the filters and the profile.
  const narrows = DIMENSIONS.some((dimension) => narrowing[dimension] !== null);
  const load = () =>
    void Promise.allSettled([
      api.get<ProblemList>(`/api/v1/problems${apiQuery(filters, LIST_FILTERS, DIMENSIONS)}`),
      api.get<NextPick>(`/api/v1/next${apiQuery(filters, NEXT_FILTERS, LABEL_DIMENSIONS)}`),
      api.get<SetList>("/api/v1/sets"),
      narrows || LIST_FILTERS.some((key) => filters[key]) ? api.get<ProblemList>(`/api/v1/problems${wideQuery(DIMENSIONS)}`) : undefined,
    ]).then(([list, pick, sets, whole]) => {
      if (pick.status === "fulfilled") next.replaceChildren(nextHeading(), ...nextPick(context, pick.value, filters));
      else showFailure(next, pick.reason);
      const known = sets.status === "fulfilled" ? sets.value.sets : [];
      fillSetChoices(bar.form, known);
      const brokenSets = sets.status === "rejected" ? [failure(sets.reason)] : [];
      const everything = whole.status === "rejected" ? null : (whole.value ?? (list.status === "fulfilled" ? list.value : null));
      if (everything !== null) shell.setAttempts(everything.entries);
      if (list.status === "rejected") {
        showFailure(table, list.reason);
        return;
      }
      const { entries, today, selected_jdk: selectedJdk, set: inSet } = list.value;
      table.removeAttribute("aria-busy");
      // The rows the profile keeps of those the other filters leave, the search apart.
      profile = profileChip([{ shown: entries.length, whole: entries.length + list.value.profile.hidden.problems, noun: null }], narrowedBy(list.value.profile));
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
          shell.setStatus({ mode: "LIST", where: `${counted(found.length, "problem")} · ${today}` });
          tally = countWords(found.length, everything?.entries.length ?? null);
          showRoute();
          if (!bar.line.hidden) shell.announce(`showing ${tally}`);
        };
        narrow();
      };
      drawRows();
    });
  load();
  const detach = bar.attach();
  return detach;
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
    h("div", { role: "group", "aria-label": "The columns of the table" }, ...boxes.map((box) => h("label", { class: "column-choice", for: box.id }, box, " ", columnLabel(box.value as ProblemColumn)))),
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
    h("caption", { class: "sr-only" }, "Problems matching the filters"),
    h("thead", {}, h("tr", {}, ...columns.map((name) => h("th", { scope: "col", "data-column": name }, columnLabel(name))))),
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

/** `needs docker postgres`, from the manifest alone, as `cstudy list` marks it; null for a problem that needs nothing more. */
function needsTag(entry: ListEntry): HTMLElement | null {
  const markers = needMarkers(entry.requires);
  if (!markers.length) return null;
  return h("span", { class: "tag needs-tag", title: `needs ${markers.join(", ")}: the Problem view lists sizes and memory` }, `needs ${markers.join(" ")}`);
}

function labelsOf(labels: readonly string[]): string {
  return labels.length ? labels.join(", ") : "–";
}

/** Each column's cell of a row. */
const CELLS: Readonly<Record<ProblemColumn, (entry: ListEntry, drawing: RowDrawing) => HTMLTableCellElement>> = {
  checked_by: (entry) => h("td", { class: "quiet" }, checkedWords(entry.checked_by)),
  problem: (entry) =>
    h(
      "td",
      { class: "title-cell" },
      h("a", { href: problemHash(entry.slug), class: "problem-link" }, entry.title),
      h("span", { class: "slug" }, entry.slug),
      entry.content === "draft" ? h("span", { class: "tag" }, "draft") : null,
      entry.source === "workspace" ? h("span", { class: "tag" }, "yours") : null,
      needsTag(entry),
    ),
  difficulty: (entry) => h("td", { class: `diff diff-${entry.difficulty}` }, entry.difficulty),
  pattern: (entry) => h("td", {}, entry.patterns[0] ?? entry.track),
  kind: (entry) => h("td", { class: "quiet" }, entry.kind),
  scope: (entry) => h("td", { class: "quiet" }, entry.scope ?? "–"),
  domain: (entry) => h("td", { class: "quiet" }, labelsOf(entry.domains)),
  role: (entry) => h("td", { class: "quiet" }, labelsOf(entry.job_roles)),
  status: (entry) => {
    const status = problemBadge(entry.status, entry.levels);
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
    { class: selfGraded(entry.kind) ? "is-self-graded" : null },
    ...columns.map((column) => {
      const cell = CELLS[column](entry, drawing);
      cell.dataset["column"] = column;
      return cell;
    }),
  );
}

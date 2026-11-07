/**
 * The Problems view (docs/specs/web-ui.md#problems-view): the `cstudy next` pick, the `cstudy list`
 * filters, kept in the fragment's query, and the table, items after problems.
 */

import "./problems.css";

import { listCommand, nextCommand, NEXT_FILTERS, startCommand } from "../commands.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { badge, command, h, isTyping } from "../dom.ts";
import { problemBadge, statusWords } from "../format.ts";
import { jdkRefusals, type SelectedJdk } from "../jdk.ts";
import { matchesSearch } from "../problems-model.ts";
import { attemptHash, FILTER_KEYS, type FilterKey, type Filters, problemHash, problemsHash } from "../routes.ts";
import { setControl, setsHolding } from "../setControl.ts";
import { empty, failure, loading, showFailure } from "../states.ts";
import type { ListEntry, NextPick, ProblemList, SetList, SetSummary } from "../types.ts";

const DIFFICULTIES = ["easy", "medium", "hard"];
const STATUSES = ["new", "in_progress", "attempted", "passed", "due", "mastered"];
/** The filters the server answers; the search narrows the rows already here. */
const LIST_FILTERS = FILTER_KEYS.filter((key) => key !== "search");
const CONTENT = ["draft", "ready"];
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
  const choices: Readonly<Record<Exclude<FilterKey, "pattern" | "search">, readonly string[]>> = {
    set: filters.set ? [filters.set] : [],
    track: session.tracks,
    kind: session.kinds,
    lang: session.languages,
    difficulty: DIFFICULTIES,
    status: STATUSES,
    content: CONTENT,
    domain: session.domains,
    role: session.job_roles,
    scope: session.scopes,
  };
  let searched = filters.search ?? "";
  const route = (): Filters => ({ ...filters, search: searched.trim() });
  let narrow: (text: string) => void = () => {};
  const form = filterForm(route, choices, (text) => {
    searched = text;
    history.replaceState(null, "", problemsHash(route()));
    shell.setCommand(listCommand(route()));
    narrow(text);
  });
  shell.main.replaceChildren(
    h("h1", { class: "sr-only" }, "Problems"),
    next,
    form,
    table,
  );
  next.replaceChildren(h("h2", { id: "next-heading", class: "eyebrow" }, "next"), loading("picking…"));

  // The pick and the table show together: the pick changes the height of the card above the
  // table, so a table drawn first would move under a pointer about to click a row.
  const load = () =>
    void Promise.allSettled([
      api.get<ProblemList>(`/api/v1/problems${queryOf(filters, LIST_FILTERS)}`),
      api.get<NextPick>(`/api/v1/next${queryOf(filters, NEXT_FILTERS)}`),
      api.get<SetList>("/api/v1/sets"),
    ]).then(([list, pick, sets]) => {
      if (pick.status === "fulfilled") next.replaceChildren(h("h2", { id: "next-heading", class: "eyebrow" }, "next"), ...nextPick(pick.value, filters));
      else showFailure(next, pick.reason);
      const known = sets.status === "fulfilled" ? sets.value.sets : [];
      fillSetChoices(form, known, filters.set);
      const brokenSets = sets.status === "rejected" ? [failure(sets.reason)] : [];
      if (list.status === "rejected") {
        showFailure(table, list.reason);
        return;
      }
      const { entries, today, selected_jdk: selectedJdk, set: inSet } = list.value;
      shell.setAttempts(entries);
      table.removeAttribute("aria-busy");
      // Unticking the set a row is listed under takes the row out, once its dialog closes.
      const drawControl = (slug: string) =>
        setControl(context, slug, {
          held: setsHolding(known, slug),
          closed: (names) => {
            if (filters.set && !names.includes(filters.set)) {
              load();
              table.focus({ preventScroll: true });
            }
          },
        });
      const rows = listing(entries, selectedJdk, drawControl);
      table.replaceChildren(
        ...brokenSets,
        ...(inSet?.missing.length ? [h("p", { class: "quiet" }, `missing from the catalog: ${inSet.missing.join(", ")}`)] : []),
        ...rows.nodes,
      );
      narrow = (text) => {
        const found = rows.narrow(text);
        const items = found.filter((entry) => entry.kind === "item").length;
        shell.setStatus({ mode: "LIST", where: `${found.length - items} problems · ${items} items · ${today}` });
      };
      narrow(searched);
    });
  load();
  const focusSearch = (event: KeyboardEvent) => {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target) || document.querySelector("dialog[open]")) return;
    event.preventDefault();
    form.querySelector<HTMLInputElement>("#filter-search")?.focus();
  };
  document.addEventListener("keydown", focusSearch);
  return () => document.removeEventListener("keydown", focusSearch);
}

/** The sets arrive after the form is drawn; the filter keeps what the route names. */
function fillSetChoices(form: HTMLFormElement, sets: readonly SetSummary[], chosen: string | undefined): void {
  const select = form.querySelector("#filter-set");
  const names = sets.map((found) => found.name).filter((name) => name !== chosen);
  select?.append(...names.map((value) => h("option", { value }, value)));
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

/** The pick; a resume links to its attempt, and the others in progress follow it, to pick another. */
export function nextPick(pick: NextPick, filters: Filters): Node[] {
  if (pick.pick === null) return [h("p", { class: "next-line" }, pick.message)];
  return [
    h(
      "p",
      { class: "next-line" },
      h("span", { class: `pick pick-${pick.pick}` }, pick.pick),
      h("a", { href: pick.attempt_id === undefined ? problemHash(pick.slug) : attemptHash(pick.attempt_id), class: "next-slug" }, pick.slug),
      h("span", { class: "quiet" }, `(${pick.difficulty} · ${pick.group})`),
      h("span", { class: "next-reason" }, pick.reason),
    ),
    h(
      "p",
      { class: "next-start" },
      h("span", { class: "quiet" }, "start "),
      command(startCommand(pick.slug, pick.language)),
      h("span", { class: "quiet" }, ` · same as ${nextCommand(filters)}`),
    ),
    ...(pick.also_open?.length
      ? [
          h(
            "p",
            { class: "next-also" },
            h("span", { class: "quiet" }, "or pick up "),
            ...pick.also_open.map((other) => h("a", { href: attemptHash(other.attempt_id), class: "resume-link" }, `↻ ${other.slug}${other.language ? ` (${other.language})` : ""}`)),
          ),
        ]
      : []),
  ];
}

function filterForm(
  route: () => Filters,
  choices: Readonly<Record<Exclude<FilterKey, "pattern" | "search">, readonly string[]>>,
  searched: (text: string) => void,
): HTMLFormElement {
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
  const selects = (Object.keys(choices) as Exclude<FilterKey, "pattern" | "search">[]).map((key) => {
    const select = h(
      "select",
      { id: `filter-${key}`, name: key },
      h("option", { value: "" }, "any"),
      ...choices[key].map((value) => h("option", { value, selected: filters[key] === value }, key === "status" ? statusWords(value) : value)),
    );
    select.addEventListener("change", () => apply(key, select.value));
    return h("label", { class: "filter", for: `filter-${key}` }, h("span", { class: "filter-name" }, key), select);
  });
  const pattern = h("input", {
    id: "filter-pattern",
    name: "pattern",
    type: "search",
    value: filters.pattern ?? "",
    placeholder: "arrays-hashing",
    spellcheck: "false",
    autocomplete: "off",
  });
  const form = h(
    "form",
    { class: "filters", role: "search", "aria-label": "Filter problems" },
    h("label", { class: "filter filter-wide", for: "filter-search" }, h("span", { class: "filter-name" }, "search"), search),
    ...selects,
    h("label", { class: "filter filter-wide", for: "filter-pattern" }, h("span", { class: "filter-name" }, "pattern"), pattern),
    Object.keys(filters).length ? h("a", { href: "#/", class: "clear" }, "clear filters") : null,
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    apply("pattern", pattern.value.trim());
  });
  pattern.addEventListener("change", () => apply("pattern", pattern.value.trim()));
  return form;
}

/** The table and what it says with no row to show; `narrow` keeps the rows a search finds. */
function listing(
  entries: readonly ListEntry[],
  selectedJdk: SelectedJdk | null,
  setsOf: (slug: string) => HTMLElement,
): { readonly nodes: readonly HTMLElement[]; narrow(text: string): readonly ListEntry[] } {
  const header = ["id", "problem", "diff", "pattern", "kind", "scope", "status", "due", "refs", "in progress", "sets"];
  const rows = entries.map((entry) => ({ entry, element: row(entry, selectedJdk, setsOf) }));
  const body = h("tbody");
  const table = h(
    "table",
    { class: "problems" },
    h("caption", { class: "sr-only" }, "Problems, then items, matching the filters"),
    h("thead", {}, h("tr", {}, ...header.map((name) => h("th", { scope: "col" }, name)))),
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

function row(entry: ListEntry, selectedJdk: SelectedJdk | null, setsOf: (slug: string) => HTMLElement): HTMLTableRowElement {
  const status = problemBadge(entry.status);
  const topic = entry.patterns[0] ?? entry.track;
  return h(
    "tr",
    { class: entry.kind === "item" ? "is-item" : null },
    h("td", { class: "num" }, entry.id ?? "–"),
    h(
      "td",
      { class: "title-cell" },
      h("a", { href: problemHash(entry.slug), class: "slug" }, entry.slug),
      h("span", { class: "title" }, entry.title),
      entry.content === "draft" ? h("span", { class: "tag" }, "draft") : null,
      entry.source === "workspace" ? h("span", { class: "tag" }, "yours") : null,
    ),
    h("td", { class: `diff diff-${entry.difficulty}` }, entry.difficulty),
    h("td", {}, topic),
    h("td", { class: "quiet" }, entry.kind),
    h("td", { class: "quiet" }, entry.scope ?? "–"),
    h("td", {}, badge(status.glyph, status.text, status.tone)),
    h("td", { class: "num quiet" }, entry.due_on ?? "–"),
    h("td", { class: "refs quiet" }, ...languageRefs(entry, selectedJdk)),
    h(
      "td",
      { class: "resume" },
      ...entry.in_progress.map((attempt) =>
        h(
          "a",
          { href: attemptHash(attempt.attempt_id), class: "resume-link", title: `Resume attempt ${attempt.attempt_id}` },
          "↻ ",
          attempt.language ?? "notes",
        ),
      ),
    ),
    h("td", {}, setsOf(entry.slug)),
  );
}

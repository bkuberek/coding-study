/**
 * The filter component (docs/specs/web-ui.md#filter-component), the one module that draws a filter
 * row: the search, the lists of a view and a More menu, the active line under them (the profile
 * chip with its counts, a chip per widened dimension and per explicit filter, the count, `clear`)
 * and the keys that go with them. A view declares what it filters; the rules are those of the
 * pure `filter-model.ts`.
 */

import "./filters.css";

import type { Cleanup } from "./context.ts";
import { type Child, h, isSearchShortcut } from "./dom.ts";
import {
  activeFilters,
  type Choice,
  type Describe,
  type Dimension,
  DIMENSIONS,
  type FilterValues,
  listShape,
  type Narrowing,
  type ProfileChip,
  unwidened,
  widenedBy,
  widenedChips,
  withChoice,
} from "./filter-model.ts";
import { requestProfileFocus, SETTINGS_HASH } from "./routes.ts";

export const SEARCH_FIELD = "filter-search";
const MORE_MENU = ".filter-menu[open]";

/** The id a chip of the active line has, which the focus goes to when a neighbor is removed. */
const chipId = (key: string): string => `chip-${key}`;
const widenedChipId = (dimension: Dimension): string => `chip-widen-${dimension}`;

/** The id of the control that takes the focus once a change has drawn the view again: a change of
 * a view that reads the server again draws it anew, so the id waits here until the next bar is built. */
let pendingFocus: string | null = null;

/** Gives the focus to the control a change left it on, in the line or the form just drawn. */
function settle(root: ParentNode): void {
  const target = pendingFocus === null ? null : root.querySelector<HTMLElement>(`#${pendingFocus}`);
  pendingFocus = null;
  target?.closest("details")?.setAttribute("open", "");
  target?.focus({ preventScroll: true });
}

/** A list of a view's filters: the key of its route and its flag, and its choices. */
export interface ListFilter {
  readonly key: string;
  readonly choices: readonly Choice[];
}

export interface ActiveLineOptions {
  /** The filters that show as chips, in the route's order. */
  readonly keys: readonly string[];
  /** The profile dimensions the view's `widen` names. */
  readonly widens: readonly Dimension[];
  readonly describe?: Describe | undefined;
  /** Whether the line ends with the count and `clear`, as a view with a list has. */
  readonly tally: boolean;
  /** Where the focus goes when no neighbor chip is left. */
  readonly fallback: string;
  readonly change: (next: FilterValues) => void;
  readonly cleared?: () => void;
  /** The route that `clear` empties. */
  readonly clearHref?: string;
}

export interface LineState {
  readonly filters: FilterValues;
  readonly count: string;
  readonly profile: ProfileChip | null;
  /** Whether a search is typed, which shows the line without a chip. */
  readonly searching: boolean;
}

export interface ActiveLine {
  readonly element: HTMLElement;
  show(state: LineState): void;
}

/**
 * What the filters leave, under the row: the profile chip with `edit profile`, the chip of each
 * widened dimension, a chip per explicit filter, then the count and `clear`. It takes no space
 * while nothing is active.
 */
export function activeLine(options: ActiveLineOptions): ActiveLine {
  const element = h("div", { class: "filter-summary" });
  const count = h("span", { class: "filter-count" });
  const clear = h("a", { href: options.clearHref ?? "#/", id: "filter-clear", class: "clear" }, "clear");
  clear.addEventListener("click", (event) => {
    event.preventDefault();
    pendingFocus = options.fallback;
    options.cleared?.();
  });
  const tally = h("span", { class: "filter-tally" }, count, h("span", { class: "quiet" }, " · "), clear);
  const show = ({ filters, count: counted, profile, searching }: LineState) => {
    const explicit = activeFilters(filters, options.keys, options.describe);
    const widened = widenedChips(filters, options.widens);
    const ids = [...widened.map((chip) => widenedChipId(chip.dimension)), ...explicit.map(({ key }) => chipId(key))];
    const neighbor = (id: string): string => ids[ids.indexOf(id) + 1] ?? ids[ids.indexOf(id) - 1] ?? options.fallback;
    const chip = (id: string, words: string, name: string, remove: FilterValues) => {
      const button = h("button", { type: "button", id, class: "filter-chip", "aria-label": name }, words, " ", h("span", { "aria-hidden": "true" }, "×"));
      button.addEventListener("click", () => {
        pendingFocus = neighbor(id);
        options.change(remove);
      });
      return button;
    };
    const chips: HTMLElement[] = [];
    if (profile !== null) {
      const button = h(
        "button",
        { type: "button", id: chipId("profile"), class: "filter-chip profile-chip", "aria-label": profile.name },
        h("span", { class: "chip-counts" }, profile.counts),
        ` · ${profile.narrowed} `,
        h("span", { "aria-hidden": "true" }, "×"),
      );
      button.addEventListener("click", () => {
        // The chip goes with the widening, so its neighbor is the first chip that takes its place.
        pendingFocus = widenedChipId(profile.dimensions.find((dimension) => options.widens.includes(dimension)) ?? DIMENSIONS[0]);
        options.change(widenedBy(filters, profile, options.widens));
      });
      chips.push(button, h("a", { href: SETTINGS_HASH, class: "edit-profile", onclick: () => requestProfileFocus() }, "edit profile"));
    }
    chips.push(...widened.map(({ dimension, words }) => chip(widenedChipId(dimension), words, `Remove the filter ${words}`, unwidened(filters, dimension, options.widens))));
    chips.push(...explicit.map(({ key, words }) => chip(chipId(key), words, `Remove the filter ${words}`, { ...filters, [key]: "" })));
    count.textContent = counted;
    // The line is drawn again as the counts change, so the chip that has the focus gets it back.
    const held = element.contains(document.activeElement) ? (document.activeElement as HTMLElement).id : "";
    element.replaceChildren(...chips, ...(options.tally ? [tally] : []));
    element.hidden = chips.length === 0 && !searching;
    if (held !== "") element.querySelector<HTMLElement>(`#${held}`)?.focus({ preventScroll: true });
    settle(document);
  };
  return { element, show };
}

/** A menu that a click elsewhere (`FilterBar.attach`), Escape and tabbing out of it close. */
export function filterMenu(name: string, label: readonly Child[], ...content: Child[]): HTMLDetailsElement {
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

/** A click outside an open menu closes it. */
function closeMenus(event: MouseEvent): void {
  for (const menu of document.querySelectorAll<HTMLDetailsElement>(MORE_MENU)) {
    if (!menu.contains(event.target as Node)) menu.open = false;
  }
}

export interface FilterBarOptions {
  /** What the view filters, in the label of its form: `Filter problems`. */
  readonly name: string;
  readonly search: { readonly placeholder: string; readonly label: string };
  /** The route's filters, the search included. */
  readonly filters: FilterValues;
  /** Every key of the route that holds a filter, in its order. */
  readonly keys: readonly string[];
  /** The lists of the slim row, and those under More (no menu while there are none). */
  readonly row: readonly ListFilter[];
  readonly more?: readonly ListFilter[];
  /** What the session's profile narrows, and the dimensions the view's route can widen. */
  readonly narrowing: Narrowing;
  readonly widens: readonly Dimension[];
  readonly describe?: Describe | undefined;
  /** What a change of the filters does: the view puts them in its route, and draws what follows. */
  readonly change: (next: FilterValues) => void;
  /** Called as the search is typed, with its text. */
  readonly searched: (text: string) => void;
  /** Controls drawn beside the form, such as the Problems view's columns menu. */
  readonly beside?: readonly HTMLElement[];
  readonly clearHref: string;
}

export interface FilterBar {
  /** The row: the form and what is beside it. */
  readonly row: HTMLElement;
  readonly form: HTMLFormElement;
  readonly line: HTMLElement;
  /** The search as typed. */
  search(): string;
  /** Draws the active line, and takes the lists to the filters of the route. */
  show(state: Omit<LineState, "searching"> & { readonly searching?: boolean }): void;
  /** Listens for `/` and for a click that closes More; the function returned stops. */
  attach(): Cleanup;
}

export function filterBar(options: FilterBarOptions): FilterBar {
  let filters = options.filters;
  const search = h("input", {
    id: SEARCH_FIELD,
    name: "search",
    type: "search",
    value: filters["search"] ?? "",
    placeholder: options.search.placeholder,
    spellcheck: "false",
    autocomplete: "off",
    "aria-keyshortcuts": "/",
  });
  const current = (): FilterValues => ({ ...filters, search: search.value.trim() });
  search.addEventListener("input", () => options.searched(search.value));

  const lists = new Map<string, { readonly filter: ListFilter; readonly blank: string; readonly select: HTMLSelectElement }>();
  const select = (filter: ListFilter, blank: string): HTMLSelectElement => {
    const shape = listShape(filter.key, blank, filter.choices, filters, options.narrowing, options.widens);
    const list = h(
      "select",
      { id: `filter-${filter.key}`, name: filter.key, class: shape.value ? "is-set" : null },
      ...shape.options.map(({ value, words }) => h("option", { value, selected: shape.value === value }, words)),
    );
    list.addEventListener("change", () => {
      pendingFocus = list.id;
      options.change(withChoice(current(), filter.key, list.value, options.narrowing, options.widens));
    });
    lists.set(filter.key, { filter, blank, select: list });
    return list;
  };
  const inRow = options.row.map((filter) => h("label", { class: "filter", for: `filter-${filter.key}` }, h("span", { class: "sr-only" }, filter.key), select(filter, filter.key)));
  const under = options.more ?? [];
  const inMore = under.filter((filter) => Boolean(listShape(filter.key, "", filter.choices, filters, options.narrowing, options.widens).value)).length;
  const form = h(
    "form",
    { class: "filters", role: "search", "aria-label": `Filter ${options.name}` },
    h("label", { class: "filter-search", for: search.id }, h("span", { class: "sr-only" }, options.search.label), h("span", { class: "filter-prompt", "aria-hidden": "true" }, ">"), search),
    ...inRow,
    under.length
      ? filterMenu(
          "filter-more",
          ["more", inMore ? h("span", { class: "filter-more-count" }, inMore, h("span", { class: "sr-only" }, " active")) : null],
          ...under.map((filter) =>
            h("label", { class: "filter-field", for: `filter-${filter.key}` }, h("span", { class: "filter-name" }, filter.key), select(filter, "any")),
          ),
        )
      : null,
  );
  form.addEventListener("submit", (event) => event.preventDefault());

  const line = activeLine({
    keys: options.keys,
    widens: options.widens,
    describe: options.describe,
    tally: true,
    fallback: SEARCH_FIELD,
    change: (next) => options.change({ ...next, search: search.value.trim() }),
    cleared: () => {
      search.value = "";
      options.change({});
    },
    clearHref: options.clearHref,
  });
  const row = h("div", { class: "filter-bar" }, form, ...(options.beside ?? []));

  const bar: FilterBar = {
    row,
    form,
    line: line.element,
    search: () => search.value,
    show(state) {
      filters = state.filters;
      for (const { filter, blank, select: list } of lists.values()) {
        const shape = listShape(filter.key, blank, filter.choices, filters, options.narrowing, options.widens);
        list.value = shape.value;
        list.classList.toggle("is-set", shape.value !== "");
      }
      line.show({ ...state, searching: state.searching ?? search.value.trim() !== "" });
    },
    attach() {
      const focusSearch = (event: KeyboardEvent) => {
        if (!isSearchShortcut(event)) return;
        event.preventDefault();
        search.focus();
      };
      document.addEventListener("keydown", focusSearch);
      document.addEventListener("click", closeMenus);
      return () => {
        document.removeEventListener("keydown", focusSearch);
        document.removeEventListener("click", closeMenus);
      };
    },
  };
  return bar;
}

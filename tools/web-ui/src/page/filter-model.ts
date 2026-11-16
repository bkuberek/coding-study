/**
 * The rules of the filter component (docs/specs/web-ui.md#filter-component), apart from the page so
 * the tests read them without a browser: the learner profile's dimensions, the widening kept in the
 * route, the choices of a profile list, the chips of an active line, and the profile chip with its
 * counts.
 */

import type { Session } from "./types.ts";

/** The learner profile's dimensions, each the name of its filter in the route and of its flag. */
export const DIMENSIONS = ["lang", "role", "domain"] as const;
export type Dimension = (typeof DIMENSIONS)[number];
/** The dimensions `cstudy next`, `cstudy mock` and `cstudy learn` take: a pick starts in a
 * workspace language, and a guide has none. */
export const LABEL_DIMENSIONS: readonly Dimension[] = ["role", "domain"];

/** The choice of a profile list that widens it; `your profile` is the empty value. */
export const ANY = "any";
const WIDEN_ALL = "all";
const CHIP_JOINER = " · ";

export function isDimension(key: string): key is Dimension {
  return (DIMENSIONS as readonly string[]).includes(key);
}

/**
 * The dimensions a route's `widen` names, in the order `lang`, `role`, `domain`, each once, those
 * `allowed` only; `all` is every one of them. A value that is none of those is dropped.
 */
export function widenedDimensions(text: string | undefined, allowed: readonly Dimension[] = DIMENSIONS): readonly Dimension[] {
  const named = (text ?? "").split(",").map((part) => part.trim());
  return DIMENSIONS.filter((dimension) => allowed.includes(dimension) && (named.includes(dimension) || named.includes(WIDEN_ALL)));
}

/** The route's `widen`: the dimensions as a comma-separated list in the canonical order. */
export function widenText(dimensions: readonly Dimension[]): string {
  return DIMENSIONS.filter((dimension) => dimensions.includes(dimension)).join(",");
}

/** What a view's filters hold, each key's value or nothing. */
export type FilterValues = Readonly<Partial<Record<string, string>>>;

/** The dimensions the route widens and names no value for: an explicit filter replaces the profile
 * in its dimension, so a widening beside it changes nothing more. */
export function widenedWithoutValue(filters: FilterValues, allowed: readonly Dimension[] = DIMENSIONS): readonly Dimension[] {
  return widenedDimensions(filters["widen"], allowed).filter((dimension) => !filters[dimension]);
}

/** The values of each profile dimension while the profile narrows it; null while it holds them all. */
export type Narrowing = Readonly<Record<Dimension, readonly string[] | null>>;
export const NARROWS_NOTHING: Narrowing = { lang: null, role: null, domain: null };

/** What the session's profile narrows: a dimension narrows when it holds fewer values than the
 * session's own list (for roles, than the list without `general`, which always shows). */
export function sessionNarrowing(session: Pick<Session, "languages" | "job_roles" | "domains" | "profile">): Narrowing {
  const { profile } = session;
  const anyRole = session.job_roles.filter((role) => role !== "general");
  return {
    lang: profile.languages.length < session.languages.length ? profile.languages : null,
    role: profile.job_roles.length < anyRole.length ? profile.job_roles : null,
    domain: profile.domains.length < session.domains.length ? profile.domains : null,
  };
}

/** What the server's `profile` of a list says narrowed it this run: the profile's values of each
 * dimension that narrowed the rows, null for each that did not. */
export interface ServedProfile {
  readonly languages: readonly string[] | null;
  readonly job_roles: readonly string[] | null;
  readonly domains: readonly string[] | null;
}

export function narrowedBy(served: ServedProfile): Narrowing {
  return { lang: served.languages, role: served.job_roles, domain: served.domains };
}

export interface Choice {
  readonly value: string;
  readonly words: string;
}

/** A filter's list as the component draws it. */
export interface ListShape {
  readonly options: readonly Choice[];
  /** The value the list holds. */
  readonly value: string;
}

/**
 * A list's options and its value. While the profile narrows its dimension the first choice reads
 * `your profile`, chosen while the route names nothing for it, then `any`, which widens; otherwise
 * the first choice is `blank`. A value the route names that the choices lack stays a choice.
 */
export function listShape(
  key: string,
  blank: string,
  choices: readonly Choice[],
  filters: FilterValues,
  narrowing: Narrowing,
  allowed: readonly Dimension[] = DIMENSIONS,
): ListShape {
  const chosen = filters[key] ?? "";
  const named = chosen !== "" && !choices.some((choice) => choice.value === chosen) ? [{ value: chosen, words: chosen }] : [];
  const profile = isDimension(key) && allowed.includes(key) && narrowing[key] !== null;
  const head: readonly Choice[] = profile
    ? [
        { value: "", words: "your profile" },
        { value: ANY, words: ANY },
      ]
    : [{ value: "", words: blank }];
  const widened = profile && widenedDimensions(filters["widen"], allowed).includes(key as Dimension);
  return { options: [...head, ...named, ...choices], value: chosen !== "" ? chosen : widened ? ANY : "" };
}

/**
 * The filters after a list takes `value`. In a profile dimension `any` widens it, in the route, and
 * `your profile` (the empty value) or a value gives it back to the profile or names the value, so
 * either way the widening of that dimension goes.
 */
export function withChoice(filters: FilterValues, key: string, value: string, narrowing: Narrowing, allowed: readonly Dimension[] = DIMENSIONS): FilterValues {
  if (!isDimension(key) || !allowed.includes(key) || narrowing[key] === null) return { ...filters, [key]: value };
  const others = widenedDimensions(filters["widen"], allowed).filter((dimension) => dimension !== key);
  if (value === ANY) return { ...filters, [key]: "", widen: widenText([...others, key]) };
  return { ...filters, [key]: value, widen: widenText(others) };
}

/** A filter's value in words, by key; the default reads the value itself. */
export type Describe = (key: string, value: string) => string;

export interface ActiveFilter {
  readonly key: string;
  readonly value: string;
  /** `domain: security`, as its chip reads. */
  readonly words: string;
}

/** Each filter of `keys` that holds a value, as its chip reads; the search has none, since its
 * field already shows it. */
export function activeFilters(filters: FilterValues, keys: readonly string[], describe: Describe = (_key, value) => value): readonly ActiveFilter[] {
  return keys.flatMap((key) => {
    const value = filters[key];
    return key === "search" || key === "widen" || !value ? [] : [{ key, value, words: `${key}: ${describe(key, value)}` }];
  });
}

export interface WidenedChip {
  readonly dimension: Dimension;
  /** `language: any`, as its chip reads. */
  readonly words: string;
}

const DIMENSION_WORDS: Readonly<Record<Dimension, string>> = { lang: "language", role: "role", domain: "domain" };

/** A chip per dimension the route widens, `language: any`, whose removal gives it back to the profile. */
export function widenedChips(filters: FilterValues, allowed: readonly Dimension[] = DIMENSIONS): readonly WidenedChip[] {
  return widenedWithoutValue(filters, allowed).map((dimension) => ({ dimension, words: `${DIMENSION_WORDS[dimension]}: any` }));
}

/** How many rows show of those the profile leaves, and of those it would without narrowing. */
export interface Counted {
  readonly shown: number;
  readonly whole: number;
  /** `guides`: said after a count when a chip counts two lists; none for one. */
  readonly noun: string | null;
}

export interface ProfileChip {
  /** `120 of 400 · your profile: python, go · backend`. */
  readonly text: string;
  /** The counts alone, which the chip draws in the muted ink, and what follows them. */
  readonly counts: string;
  readonly narrowed: string;
  /** `Show all 400: your profile shows 120, languages python, go; roles backend and general`. */
  readonly name: string;
  /** The dimensions it widens. */
  readonly dimensions: readonly Dimension[];
}

const PHRASES: Readonly<Record<Dimension, string>> = { lang: "languages", role: "roles", domain: "domains" };

function phrase(dimension: Dimension, values: readonly string[]): string {
  return dimension === "role" ? `roles ${values.join(", ")} and general` : `${PHRASES[dimension]} ${values.join(", ")}`;
}

function noun(count: Counted): string {
  return count.noun === null ? "" : ` ${count.noun}`;
}

/**
 * The quiet chip of the profile's part in a view: null while it hid nothing of the rows the other
 * filters leave, or narrowed no dimension this run. Its counts leave the search out.
 */
export function profileChip(counts: readonly Counted[], narrowed: Narrowing): ProfileChip | null {
  const dimensions = DIMENSIONS.filter((dimension) => narrowed[dimension] !== null);
  if (dimensions.length === 0 || !counts.some((count) => count.shown < count.whole)) return null;
  const values = dimensions.map((dimension) => (narrowed[dimension] ?? []).join(", "));
  const tallied = counts.map((count) => `${count.shown} of ${count.whole}${noun(count)}`).join(CHIP_JOINER);
  const kept = `your profile: ${values.join(CHIP_JOINER)}`;
  const whole = counts.map((count) => `${count.whole}${noun(count)}`).join(" and ");
  const shows = counts.map((count) => `${count.shown}${noun(count)}`).join(" and ");
  const phrases = dimensions.map((dimension) => phrase(dimension, narrowed[dimension] ?? []));
  return {
    text: `${tallied}${CHIP_JOINER}${kept}`,
    counts: tallied,
    narrowed: kept,
    name: `Show all ${whole}: your profile shows ${shows}, ${phrases.join("; ")}`,
    dimensions,
  };
}

/** The route after the profile chip widens each dimension it names. */
export function widenedBy(filters: FilterValues, chip: ProfileChip, allowed: readonly Dimension[] = DIMENSIONS): FilterValues {
  return { ...filters, widen: widenText([...widenedDimensions(filters["widen"], allowed), ...chip.dimensions.filter((dimension) => allowed.includes(dimension))]) };
}

/** The route after a widened dimension's chip is removed: the profile applies there again. */
export function unwidened(filters: FilterValues, dimension: Dimension, allowed: readonly Dimension[] = DIMENSIONS): FilterValues {
  return { ...filters, widen: widenText(widenedDimensions(filters["widen"], allowed).filter((found) => found !== dimension)) };
}

/**
 * The `--widen` flags of a command that takes `takes`: `--widen all` once the route widens every
 * dimension the command takes, else one flag per widened dimension; a dimension the route names a
 * value for is left out of the second, since that value replaces the profile there.
 */
export function widenFlags(filters: FilterValues, takes: readonly Dimension[]): readonly string[] {
  const widened = widenedDimensions(filters["widen"], takes);
  if (widened.length === 0) return [];
  if (widened.length === takes.length) return [`--widen ${WIDEN_ALL}`];
  return widened.filter((dimension) => !filters[dimension]).map((dimension) => `--widen ${dimension}`);
}

/** The route's filters as the server's query: each named filter, and `widen` once per dimension
 * the endpoint takes. */
export function apiQuery(filters: FilterValues, keys: readonly string[], takes: readonly Dimension[]): string {
  const query = new URLSearchParams();
  for (const key of keys) {
    if (key === "widen") {
      for (const dimension of widenedWithoutValue(filters, takes)) query.append("widen", dimension);
      continue;
    }
    const value = filters[key];
    if (value) query.set(key, value);
  }
  const text = query.toString();
  return text ? `?${text}` : "";
}

/** Every dimension widened, for a read of the whole list that ignores the profile. */
export function wideQuery(takes: readonly Dimension[]): string {
  return `?${takes.map((dimension) => `widen=${dimension}`).join("&")}`;
}

/** Every problem, whatever the profile: what the count is out of, the menu of attempts in progress,
 * the reviews of the Progress view and the problems of your own, which the profile never filters. */
export const ALL_PROBLEMS = `/api/v1/problems${wideQuery(DIMENSIONS)}`;

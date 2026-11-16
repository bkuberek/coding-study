/**
 * The page's views, addressed by the URL's fragment so the server serves only `/`
 * (docs/specs/web-ui.md#page). The Problems and Guides views keep their filters, and the widening
 * of the learner profile, in the fragment's query.
 */

import { DIMENSIONS, type Dimension, LABEL_DIMENSIONS, widenedDimensions, widenText } from "./filter-model.ts";

/** The filters of the Problems view, as `cstudy list` names them, `widen` (the dimensions of the
 * learner profile the route drops, as `--widen`) before the languages. */
export const FILTER_KEYS = ["set", "track", "kind", "checked", "widen", "lang", "difficulty", "status", "content", "domain", "role", "scope", "pattern", "search"] as const;
export type FilterKey = (typeof FILTER_KEYS)[number];
export type Filters = Partial<Record<FilterKey, string>>;

/** The filters and the search of the Guides view (docs/specs/web-ui.md#guides-view), the search
 * last as in `FILTER_KEYS`. A guide has no language, so its `widen` names roles and domains only. */
export const GUIDE_FILTER_KEYS = ["domain", "role", "widen", "level", "path", "status", "search"] as const;
export type GuideFilterKey = (typeof GUIDE_FILTER_KEYS)[number];
export type GuideFilters = Partial<Record<GuideFilterKey, string>>;

export type Route =
  | { readonly view: "problems"; readonly filters: Filters }
  | { readonly view: "problem"; readonly slug: string }
  | { readonly view: "sets" }
  | { readonly view: "set"; readonly name: string }
  | { readonly view: "guides"; readonly filters: GuideFilters }
  | { readonly view: "guide"; readonly slug: string }
  | { readonly view: "path"; readonly slug: string }
  | { readonly view: "docs"; readonly search: string }
  | { readonly view: "doc"; readonly slug: string; readonly heading: string | null }
  | { readonly view: "attempt"; readonly id: number }
  | { readonly view: "mock" }
  | { readonly view: "progress" }
  | { readonly view: "health" }
  | { readonly view: "settings" }
  | { readonly view: "about" }
  | { readonly view: "missing"; readonly fragment: string };

/** The views addressed by one segment, such as `#/health`. */
const SINGLE_VIEWS = ["sets", "mock", "progress", "health", "settings", "about"] as const;
type SingleView = (typeof SINGLE_VIEWS)[number];

function isSingleView(segment: string): segment is SingleView {
  return (SINGLE_VIEWS as readonly string[]).includes(segment);
}

export function parseRoute(fragment: string): Route {
  const hash = fragment.startsWith("#") ? fragment.slice(1) : fragment;
  const [path = "", query = ""] = hash.split("?", 2);
  const segments = path.split("/").filter((segment) => segment !== "");
  const [first, second, ...rest] = segments;
  if (first === undefined) return { view: "problems", filters: filtersOf(new URLSearchParams(query), FILTER_KEYS, DIMENSIONS) };
  if (first === "guides" && second === undefined) return { view: "guides", filters: filtersOf(new URLSearchParams(query), GUIDE_FILTER_KEYS, LABEL_DIMENSIONS) };
  if (first === "problems" && second !== undefined && rest.length === 0) {
    return { view: "problem", slug: decodeURIComponent(second) };
  }
  if (first === "sets" && second !== undefined && rest.length === 0) return { view: "set", name: decodeURIComponent(second) };
  if (first === "guides" && second !== undefined && rest.length === 0) return { view: "guide", slug: decodeURIComponent(second) };
  if (first === "paths" && second !== undefined && rest.length === 0) return { view: "path", slug: decodeURIComponent(second) };
  if (first === "docs" && second === undefined) return { view: "docs", search: new URLSearchParams(query).get("search") ?? "" };
  if (first === "docs" && second !== undefined && rest.length <= 1) {
    const [heading] = rest;
    return { view: "doc", slug: decodeURIComponent(second), heading: heading === undefined ? null : decodeURIComponent(heading) };
  }
  if (first === "attempts" && second !== undefined && rest.length === 0 && /^[1-9]\d*$/.test(second)) {
    return { view: "attempt", id: Number(second) };
  }
  if (segments.length === 1 && isSingleView(first)) return { view: first };
  return { view: "missing", fragment: `#${hash}` };
}

export function problemsHash(filters: Filters): string {
  const text = queryText(filters, FILTER_KEYS);
  return text ? `#/?${text}` : "#/";
}

export const problemHash = (slug: string): string => `#/problems/${encodeURIComponent(slug)}`;
export const attemptHash = (id: number): string => `#/attempts/${id}`;
export const MOCK_HASH = "#/mock";
/** The About view is linked from the status bar's version, not listed among the top bar's views. */
export const ABOUT_HASH = "#/about";
export const SETS_HASH = "#/sets";
export const setHash = (name: string): string => `${SETS_HASH}/${encodeURIComponent(name)}`;
/** The Guides view, and a guide's and a path's: where `cstudy learn <guide> --open` and
 * `cstudy learn --path <path> --open` land. */
export const GUIDES_HASH = "#/guides";
/** Settings, where `edit profile` leads. */
export const SETTINGS_HASH = "#/settings";
/** The Guides view with its search and filters, each in the query while it holds a value. */
export function guidesHash(filters: GuideFilters): string {
  const text = queryText(filters, GUIDE_FILTER_KEYS);
  return text ? `${GUIDES_HASH}?${text}` : GUIDES_HASH;
}
export const guideHash = (slug: string): string => `${GUIDES_HASH}/${encodeURIComponent(slug)}`;
export const pathHash = (slug: string): string => `#/paths/${encodeURIComponent(slug)}`;
/** The Docs view, with its search in the query, and a page or one of its headings: where
 * `cstudy docs --open` and `cstudy docs <topic> --open` land (docs/specs/user-docs.md#docs-view). */
export const DOCS_HASH = "#/docs";
export function docsHash(search: string): string {
  return search ? `${DOCS_HASH}?${new URLSearchParams({ search }).toString()}` : DOCS_HASH;
}
export function docHash(slug: string, heading: string | null = null): string {
  const page = `${DOCS_HASH}/${encodeURIComponent(slug)}`;
  return heading === null || heading === "" ? page : `${page}/${encodeURIComponent(heading)}`;
}

function queryText<Key extends string>(filters: Partial<Record<Key, string>>, keys: readonly Key[]): string {
  const query = new URLSearchParams();
  for (const key of keys) {
    const value = filters[key];
    if (value) query.set(key, value);
  }
  // The widening is a list, `widen=lang,role`: its commas stay readable.
  return query.toString().replaceAll("%2C", ",");
}

/** The filters a query holds, the widening in its canonical form and only of the dimensions the
 * view `widens`. */
function filtersOf<Key extends string>(query: URLSearchParams, keys: readonly Key[], widens: readonly Dimension[]): Partial<Record<Key, string>> {
  const filters: Partial<Record<Key, string>> = {};
  for (const key of keys) {
    const value = key === "widen" ? widenText(widenedDimensions(query.get(key) ?? "", widens)) : query.get(key);
    if (value) filters[key] = value;
  }
  return filters;
}

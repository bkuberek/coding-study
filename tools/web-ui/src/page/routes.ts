/**
 * The page's views, addressed by the URL's fragment so the server serves only `/`
 * (docs/specs/web-ui.md#page). The Problems view keeps its filters in the fragment's query.
 */

/** The filters of the Problems view, as `cstudy list` names them. */
export const FILTER_KEYS = ["set", "track", "kind", "lang", "difficulty", "status", "content", "domain", "role", "scope", "pattern", "search"] as const;
export type FilterKey = (typeof FILTER_KEYS)[number];
export type Filters = Partial<Record<FilterKey, string>>;

export type Route =
  | { readonly view: "problems"; readonly filters: Filters }
  | { readonly view: "problem"; readonly slug: string }
  | { readonly view: "sets" }
  | { readonly view: "set"; readonly name: string }
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
  if (first === undefined) return { view: "problems", filters: filtersOf(new URLSearchParams(query)) };
  if (first === "problems" && second !== undefined && rest.length === 0) {
    return { view: "problem", slug: decodeURIComponent(second) };
  }
  if (first === "sets" && second !== undefined && rest.length === 0) return { view: "set", name: decodeURIComponent(second) };
  if (first === "attempts" && second !== undefined && rest.length === 0 && /^[1-9]\d*$/.test(second)) {
    return { view: "attempt", id: Number(second) };
  }
  if (segments.length === 1 && isSingleView(first)) return { view: first };
  return { view: "missing", fragment: `#${hash}` };
}

export function problemsHash(filters: Filters): string {
  const query = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    const value = filters[key];
    if (value) query.set(key, value);
  }
  const text = query.toString();
  return text ? `#/?${text}` : "#/";
}

export const problemHash = (slug: string): string => `#/problems/${encodeURIComponent(slug)}`;
export const attemptHash = (id: number): string => `#/attempts/${id}`;
export const MOCK_HASH = "#/mock";
/** The About view is linked from the status bar's version, not listed among the top bar's views. */
export const ABOUT_HASH = "#/about";
export const SETS_HASH = "#/sets";
export const setHash = (name: string): string => `${SETS_HASH}/${encodeURIComponent(name)}`;

function filtersOf(query: URLSearchParams): Filters {
  const filters: Filters = {};
  for (const key of FILTER_KEYS) {
    const value = query.get(key);
    if (value) filters[key] = value;
  }
  return filters;
}

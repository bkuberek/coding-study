/**
 * The page's views, addressed by the URL's fragment so the server serves only `/`
 * (docs/specs/web-ui.md#page). The Problems view keeps its filters in the fragment's query.
 */

/** The filters of the Problems view, as `cstudy list` names them. */
export const FILTER_KEYS = ["track", "kind", "lang", "difficulty", "status", "content", "pattern"] as const;
export type FilterKey = (typeof FILTER_KEYS)[number];
export type Filters = Partial<Record<FilterKey, string>>;

export type Route =
  | { readonly view: "problems"; readonly filters: Filters }
  | { readonly view: "problem"; readonly slug: string }
  | { readonly view: "attempt"; readonly id: number }
  | { readonly view: "health" }
  | { readonly view: "settings" }
  | { readonly view: "terminal"; readonly command: string }
  | { readonly view: "missing"; readonly fragment: string };

/** Views the page does not have yet; it names the command that does the same. */
const TERMINAL_VIEWS: Readonly<Record<string, string>> = {
  mock: "cstudy mock",
  progress: "cstudy stats",
};

export function parseRoute(fragment: string): Route {
  const hash = fragment.startsWith("#") ? fragment.slice(1) : fragment;
  const [path = "", query = ""] = hash.split("?", 2);
  const segments = path.split("/").filter((segment) => segment !== "");
  const [first, second, ...rest] = segments;
  if (first === undefined) return { view: "problems", filters: filtersOf(new URLSearchParams(query)) };
  if (first === "problems" && second !== undefined && rest.length === 0) {
    return { view: "problem", slug: decodeURIComponent(second) };
  }
  if (first === "attempts" && second !== undefined && rest.length === 0 && /^[1-9]\d*$/.test(second)) {
    return { view: "attempt", id: Number(second) };
  }
  if (segments.length === 1 && (first === "health" || first === "settings")) return { view: first };
  const command = segments.length === 1 ? TERMINAL_VIEWS[first] : undefined;
  if (command !== undefined) return { view: "terminal", command };
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

function filtersOf(query: URLSearchParams): Filters {
  const filters: Filters = {};
  for (const key of FILTER_KEYS) {
    const value = query.get(key);
    if (value) filters[key] = value;
  }
  return filters;
}

// The route table. A feature hands the server a list of routes, and a request finds its route here.

import { HttpProblem } from "./problems.ts";

export interface Answer {
  readonly status: number;
  readonly body: unknown;
}

/** What a handler gets to work with. */
export interface ApiRequest {
  /** Decoded path parameters: `/work-orders/:id` gives `params.id`. */
  readonly params: Readonly<Record<string, string>>;
  /** The decoded query string. Every value in it is a string. */
  readonly query: URLSearchParams;
  /** Header values by name, with every name in lower case. */
  readonly headers: ReadonlyMap<string, string>;
  /** The raw request text, "" for none. */
  readonly body: string;
}

export interface Route {
  readonly method: string;
  readonly pattern: string;
  readonly handle: (request: ApiRequest) => Answer;
}

interface RawRequest {
  readonly method: string;
  readonly path: string;
  readonly headers: readonly string[];
  readonly body: string;
}

export function dispatch(routes: readonly Route[], raw: RawRequest): Answer {
  const url = new URL(raw.path, "http://work-orders.invalid");
  const onPath = routes.filter((route) => matchPath(route.pattern, url.pathname) !== null);
  if (onPath.length === 0) {
    throw new HttpProblem(404, "route_not_found", `No route for ${raw.method} ${url.pathname}`);
  }
  const route = onPath.find((candidate) => candidate.method === raw.method);
  if (route === undefined) {
    const message = `Method ${raw.method} not allowed on ${url.pathname}`;
    throw new HttpProblem(405, "method_not_allowed", message);
  }
  return route.handle({
    params: matchPath(route.pattern, url.pathname) ?? {},
    query: url.searchParams,
    headers: parseHeaders(raw.headers),
    body: raw.body,
  });
}

function matchPath(pattern: string, pathname: string): Record<string, string> | null {
  const expected = pattern.split("/");
  const actual = pathname.split("/");
  if (expected.length !== actual.length) {
    return null;
  }
  const params: Record<string, string> = {};
  for (const [index, segment] of expected.entries()) {
    const value = actual[index] ?? "";
    if (segment.startsWith(":")) {
      params[segment.slice(1)] = decodeURIComponent(value);
    } else if (segment !== value) {
      return null;
    }
  }
  return params;
}

function parseHeaders(lines: readonly string[]): Map<string, string> {
  const headers = new Map<string, string>();
  for (const line of lines) {
    const colon = line.indexOf(":");
    headers.set(line.slice(0, colon).trim().toLowerCase(), line.slice(colon + 1).trim());
  }
  return headers;
}

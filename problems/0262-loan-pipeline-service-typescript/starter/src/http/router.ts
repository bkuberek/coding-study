// A small router: patterns such as `/loans/:id`, matched segment by segment.

import { ApiError } from "../errors.ts";

export interface RequestContext {
  /** Decoded path parameters: `/loans/:id` gives `params.id`. */
  readonly params: Readonly<Record<string, string>>;
  /** The decoded query string. Every value in it is a string. */
  readonly query: URLSearchParams;
  /** The raw request text, "" for none. */
  readonly body: string;
}

/** A handler's answer; `LoanApi.request` serializes `body`. */
export interface ApiResponse {
  readonly status: number;
  readonly body: unknown;
}

export type Handler = (context: RequestContext) => ApiResponse;

interface Route {
  readonly method: string;
  readonly segments: readonly string[];
  readonly handler: Handler;
}

export class Router {
  readonly #routes: Route[] = [];

  add(method: string, pattern: string, handler: Handler): void {
    this.#routes.push({ method, segments: pattern.split("/"), handler });
  }

  /** Throws an `ApiError` when no route matches, 404 for the path and 405 for the method. */
  dispatch(method: string, target: string, body: string): ApiResponse {
    const url = new URL(target, "http://loan-api.invalid");
    const segments = url.pathname.split("/");
    const matching = this.#routes.filter((route) => segmentsMatch(route.segments, segments));
    if (matching.length === 0) {
      throw new ApiError(404, "route_not_found", `No route for ${method} ${url.pathname}`);
    }
    const route = matching.find((candidate) => candidate.method === method);
    if (route === undefined) {
      const message = `Method ${method} not allowed on ${url.pathname}`;
      throw new ApiError(405, "method_not_allowed", message);
    }
    return route.handler({ params: readParams(route.segments, segments), query: url.searchParams, body });
  }
}

function segmentsMatch(pattern: readonly string[], actual: readonly string[]): boolean {
  return (
    pattern.length === actual.length &&
    pattern.every((segment, index) => segment.startsWith(":") || segment === actual[index])
  );
}

function readParams(pattern: readonly string[], actual: readonly string[]): Record<string, string> {
  const params: Record<string, string> = {};
  pattern.forEach((segment, index) => {
    if (segment.startsWith(":")) {
      params[segment.slice(1)] = decodeURIComponent(actual[index] ?? "");
    }
  });
  return params;
}

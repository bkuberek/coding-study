// Finds the route for a request. Knows nothing about suppliers.

import { ApiError } from "./errors.ts";

export interface RouteRequest {
  method: string;
  path: string;
  params: Record<string, string>;
  body: string;
}

export interface Answer {
  status: number;
  body: unknown;
}

export interface Route {
  method: string;
  pattern: string;
  handle: (request: RouteRequest) => Answer;
}

function match(pattern: string, path: string): Record<string, string> | null {
  const wanted = pattern.split("/");
  const given = path.split("/");
  if (wanted.length !== given.length) {
    return null;
  }
  const params: Record<string, string> = {};
  for (const [index, part] of wanted.entries()) {
    const value = given[index] ?? "";
    if (part.startsWith(":")) {
      params[part.slice(1)] = value;
    } else if (part !== value) {
      return null;
    }
  }
  return params;
}

export function dispatch(routes: readonly Route[], request: Omit<RouteRequest, "params">): Answer {
  let pathExists = false;
  for (const route of routes) {
    const params = match(route.pattern, request.path);
    if (params === null) {
      continue;
    }
    pathExists = true;
    if (route.method === request.method) {
      return route.handle({ ...request, params });
    }
  }
  if (pathExists) {
    throw new ApiError(405, "method_not_allowed", `Method ${request.method} not allowed on ${request.path}`);
  }
  throw new ApiError(404, "route_not_found", `No route for ${request.method} ${request.path}`);
}

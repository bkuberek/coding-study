// GET /sites.

import type { Route } from "../shared/routing.ts";
import type { SiteDirectory } from "./directory.ts";

export function siteRoutes(sites: SiteDirectory): Route[] {
  return [
    {
      method: "GET",
      pattern: "/sites",
      handle: () => ({ status: 200, body: { items: sites.list() } }),
    },
  ];
}

// Which URLs a webhook may go to, judged on the parsed URL and never on its text.

import { ALLOWED_PORTS } from "./limits.ts";

const DEFAULT_PORTS: ReadonlyMap<string, number> = new Map([
  ["http:", 80],
  ["https:", 443],
]);

/**
 * `text` parsed as a URL a webhook may be sent to, or null: http or https, no user name or
 * password, and an allowed port. `base` resolves a relative redirect. The parser also turns every
 * spelling of an IP address into one form, so `http://0x7f.1/` has the host name `127.0.0.1`.
 */
export function webhookUrl(text: string, base?: URL): URL | null {
  const url = URL.parse(text, base);
  if (url === null || url.username !== "" || url.password !== "") {
    return null;
  }
  const defaultPort = DEFAULT_PORTS.get(url.protocol);
  if (defaultPort === undefined) {
    return null;
  }
  const port = url.port === "" ? defaultPort : Number(url.port);
  return ALLOWED_PORTS.has(port) ? url : null;
}

// The dispatcher's limits, as the statement sets them.

/** Each request sent, from connecting to the last byte of its answer. */
export const REQUEST_TIMEOUT_MS = 1000;
export const MAX_RESPONSE_BYTES = 65_536;
export const MAX_REDIRECTS = 3;
export const MAX_ATTEMPTS = 3;
/** From the end of a failed attempt to the start of the next. */
export const RETRY_WAIT_MS = 250;
export const ALLOWED_PORTS: ReadonlySet<number> = new Set([80, 443, 8080, 8443]);
export const DELIVERIES_PER_HOST = 5;
export const RATE_WINDOW_MS = 10_000;
export const FAILURES_BEFORE_DISABLING = 3;

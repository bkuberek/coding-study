// Every number the statement sets, in one place.

/** The body of any request but an upload: a scan or a link takes a few bytes of JSON. */
export const MAX_SMALL_BODY_BYTES = 1024;
export const MAX_NAME_LENGTH = 255;
/** Each request to the scanner, from sending it to the last byte of its answer. */
export const SCAN_TIMEOUT_MS = 1000;
export const SCAN_ATTEMPTS = 3;
/** The wait after the first failed attempt; it doubles after each one. */
export const FIRST_RETRY_WAIT_MS = 250;
export const MIN_LINK_SECONDS = 1;
export const MAX_LINK_SECONDS = 3600;

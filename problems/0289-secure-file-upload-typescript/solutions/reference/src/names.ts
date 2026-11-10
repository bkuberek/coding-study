// A file's name is metadata: it is shown and offered as the download's name, and never used as a
// path. Browsers that sent a whole client path, `C:\Users\kim\avatar.png`, are why both
// separators count.

import { MAX_NAME_LENGTH } from "./limits.ts";

const PRINTABLE_ASCII = /^[\x20-\x7e]+$/;

/** What follows the last `/` or `\` of the name given, or null when that cannot be shown. */
export function displayName(given: string): string | null {
  const name = given.slice(Math.max(given.lastIndexOf("/"), given.lastIndexOf("\\")) + 1);
  const showable =
    PRINTABLE_ASCII.test(name) &&
    name.length <= MAX_NAME_LENGTH &&
    !name.includes('"') &&
    name !== "." &&
    name !== "..";
  return showable ? name : null;
}

/** The part after the name's last dot, in lower case; empty when there is none. */
export function extensionOf(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot === -1 ? "" : name.slice(dot + 1).toLowerCase();
}

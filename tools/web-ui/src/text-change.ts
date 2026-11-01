/**
 * The smallest single change that turns one text into another: the common start and end stay, the
 * middle is replaced. An editor that takes a file's new version this way keeps the cursor and the
 * scroll position wherever the text around them did not change, and the change can be undone.
 * Line ends are compared as the editor keeps them, `\n`.
 */

export interface TextChange {
  /** Offsets into the old text, as the editor counts them. */
  readonly from: number;
  readonly to: number;
  readonly insert: string;
}

const LINE_END = /\r\n?/g;

/** Null when the texts are the same. */
export function textChange(before: string, after: string): TextChange | null {
  const old = before.replace(LINE_END, "\n");
  const now = after.replace(LINE_END, "\n");
  if (old === now) return null;
  const shorter = Math.min(old.length, now.length);
  let start = 0;
  while (start < shorter && old[start] === now[start]) start += 1;
  let end = 0;
  while (end < shorter - start && old[old.length - 1 - end] === now[now.length - 1 - end]) end += 1;
  return { from: start, to: old.length - end, insert: now.slice(start, now.length - end) };
}

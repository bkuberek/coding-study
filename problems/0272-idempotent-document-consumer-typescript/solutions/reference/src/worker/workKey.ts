// What identifies a piece of work: the text to read and the code that reads it.

import { createHash } from "node:crypto";

/** The hash takes the two parts apart with a separator, so ("Form-1", 2) is not ("Form-", 12). */
export function workKey(body: string, pipelineVersion: number): string {
  return createHash("sha256").update(`${pipelineVersion}\n${body}`).digest("hex");
}

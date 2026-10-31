/**
 * Requests the CLI guards with a question (docs/specs/web-ui.md#api-conventions): the server
 * changes nothing and answers 409 `confirmation_required` with the question; the page asks it and
 * sends the same request again with `confirm`.
 */

import { ApiError } from "./api.ts";

export const CONFIRMATION_REQUIRED = "confirmation_required";

/** Asks the question; resolves whether the answer was yes. */
export type Ask = (question: string) => Promise<boolean>;

/** `send(false)`; after the server's question and a yes, `send(true)`. Null after a no. */
export async function confirmed<Document>(
  send: (confirm: boolean) => Promise<Document>,
  ask: Ask,
): Promise<Document | null> {
  try {
    return await send(false);
  } catch (error) {
    if (!(error instanceof ApiError) || error.code !== CONFIRMATION_REQUIRED) throw error;
    return (await ask(error.message)) ? send(true) : null;
  }
}

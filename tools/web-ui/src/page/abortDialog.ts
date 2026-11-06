/**
 * The Abort action (docs/specs/web-ui.md#attempt-view): the question `cstudy abort` asks, which the
 * server sends, then the attempt ends as abandoned and the page opens its problem. A refusal, from
 * a run in progress or from edits that are not saved, shows in a dialog of its own. It is part of
 * the dialogs' chunk (NFR-12).
 */

import { refreshAttemptsMenu } from "./attempts.ts";
import { confirmed } from "./confirmation.ts";
import type { PageContext } from "./context.ts";
import { confirmAction, openSheet } from "./dialogs.ts";
import { problemHash } from "./routes.ts";
import { unsavedPaths } from "./save.ts";
import { failure } from "./states.ts";
import type { AttemptStatus } from "./types.ts";

export async function abortAttempt(context: PageContext, status: AttemptStatus): Promise<void> {
  const title = `abort · ${status.slug}`;
  const command = `cstudy abort ${status.slug}`;
  try {
    const unsaved = unsavedPaths();
    if (unsaved.length > 0) throw new Error(`${unsaved.join(", ")}: not saved. Abort keeps the files on disk, not unsaved edits, so save first`);
    const send = (confirm: boolean) => context.api.post<unknown>(`/api/v1/attempts/${status.attempt_id}/abort`, { confirm });
    const ask = (message: string) => confirmAction({ title, message, action: "Abort", dismiss: "Keep working", destructive: true, command });
    if ((await confirmed(send, ask)) === null) return;
  } catch (error) {
    openSheet(title).body.append(failure(error));
    return;
  }
  refreshAttemptsMenu(context);
  void context.mock.refresh();
  context.shell.announce(`aborted ${status.slug}`);
  location.hash = problemHash(status.slug);
}

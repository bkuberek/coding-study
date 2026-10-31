/**
 * The file dialogs (`fileDialogs.ts`) in a chunk of their own: it is fetched the first time a
 * question is asked, so the page loads less before a file is editable (NFR-12).
 */

import type { Confirmation, NameRequest } from "./fileDialogs.ts";

/** Resolves true once the action is confirmed, false when the dialog is dismissed. */
export async function confirmAction(confirmation: Confirmation): Promise<boolean> {
  return (await import("./fileDialogs.ts")).confirmAction(confirmation);
}

/** Resolves true once `request.submit` succeeds, false when the dialog is dismissed. */
export async function askNames(request: NameRequest): Promise<boolean> {
  return (await import("./fileDialogs.ts")).askNames(request);
}

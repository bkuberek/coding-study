/**
 * Dialogs and panes in chunks of their own, fetched the first time a control opens one, so the
 * page loads less before a file is editable (NFR-12).
 */

import type { PageContext } from "./context.ts";
import { messageOf } from "./states.ts";

/** Runs `open` with the module `load` fetches; a failed fetch is announced instead. */
export function openLazily<Module>(context: PageContext, load: () => Promise<Module>, open: (module: Module) => void): void {
  load()
    .then(open)
    .catch((error: unknown) => context.shell.announce(`could not open: ${messageOf(error)}`));
}

/** The module `load` fetches, or null when the fetch failed, which `announce` says. */
export async function fetchChunk<Module>(announce: (message: string) => void, load: () => Promise<Module>): Promise<Module | null> {
  try {
    return await load();
  } catch (error) {
    announce(`could not load: ${messageOf(error)}`);
    return null;
  }
}

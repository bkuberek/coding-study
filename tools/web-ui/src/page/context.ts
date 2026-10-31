/** What every view shares: the API, the session, the preferences and the page's chrome. */

import type { Api } from "./api.ts";
import type { Shell } from "./shell.ts";
import type { Preferences, Session } from "./types.ts";

export type PreferencesListener = (preferences: Preferences) => void;

export interface PageContext {
  readonly api: Api;
  readonly session: Session;
  /** The CSP nonce of this page, for the editor's style elements. */
  readonly nonce: string;
  readonly shell: Shell;
  preferences(): Preferences;
  /** Stores a change of preferences and tells every listener. */
  savePreferences(change: Partial<Omit<Preferences, "format">>): Promise<void>;
  /** Calls the listener after each change; the function returned removes it. */
  onPreferences(listener: PreferencesListener): () => void;
}

/** Undoes what a view set up: timers, listeners, editors. */
export type Cleanup = () => void;

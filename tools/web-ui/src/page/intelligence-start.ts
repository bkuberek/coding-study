/**
 * The Attempt view's code intelligence, started on demand (docs/specs/web-ui.md#front-end-assets):
 * the link between the editors and the sessions (`intelligence.ts`) is a module of its own, so a
 * page with `code_intelligence` off, the default, loads none of it. It is fetched when the
 * preference is on, at the view's start or once it is turned on.
 */

import type { PageContext } from "./context.ts";
import { fetchChunk } from "./lazy.ts";
import type { AttemptLanguage, IntelligenceLink } from "./intelligence.ts";
import type { EditorTabs } from "./workbench.ts";

export interface Intelligence {
  /** The attempt's language, with why it has no code intelligence if so, and its tree's root. */
  configure(attempt: AttemptLanguage, root: string): void;
  destroy(): void;
}

export function startIntelligence(context: PageContext, tabs: EditorTabs, attemptId: number): Intelligence {
  let configured: { attempt: AttemptLanguage; root: string } | null = null;
  let link: IntelligenceLink | null = null;
  let loading = false;
  let destroyed = false;
  const load = (): void => {
    if (link !== null || loading || destroyed || !context.preferences().code_intelligence) return;
    loading = true;
    void fetchChunk(
      (message) => context.shell.announce(message),
      () => import("./intelligence.ts"),
    ).then((module) => {
      loading = false;
      if (module === null || destroyed) return;
      link = new module.IntelligenceLink(context, tabs, attemptId);
      if (configured !== null) link.configure(configured.attempt, configured.root);
    });
  };
  const unsubscribe = context.onPreferences(load);
  load();
  return {
    configure(attempt, root) {
      configured = { attempt, root };
      link?.configure(attempt, root);
      load();
    },
    destroy() {
      destroyed = true;
      unsubscribe();
      link?.destroy();
    },
  };
}

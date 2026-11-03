/**
 * The sessions of this page (docs/specs/web-ui.md#code-intelligence-in-the-editor): one per root
 * the tabs show files of, kept for the language's idle time after their last file closes, so
 * going back to an attempt does not start a server again, and suspended five minutes after the
 * tab is hidden. An editor attaches with the URI and language id of its file and gets the
 * session's state; `didSave` goes out from the page's `cstudy:file-saved` event.
 */

import type { Editor } from "../editor.ts";
import { FILE_SAVED_EVENT, type FileSaved } from "../page/api.ts";
import type { SessionState } from "../page/intelligence-state.ts";
import { fileUri, rootUri } from "./documents.ts";
import { Session, type StateListener } from "./session.ts";
import type { Origin } from "./transport.ts";

/** A hidden tab's sessions close after this long. */
export const HIDDEN_CLOSE_MS = 5 * 60 * 1000;
const SECOND_MS = 1000;

export interface AttachRequest {
  readonly editor: Editor;
  readonly csrf: string;
  readonly attemptId: number;
  /** The file's path in the attempt's tree. */
  readonly path: string;
  readonly languageId: string;
  /** The session's workspace and the tree's root: the session's root is the two together. */
  readonly workspace: string;
  readonly root: string;
  /** The catalog's `idle_s` for the language. */
  readonly idleS: number;
}

/** What the manager asks of the page: whether code intelligence is on, and to hear when that changes. */
export interface PageHooks {
  enabled(): boolean;
  onPreferences(listener: () => void): () => void;
}

/** What the sessions run on; the page's own by default, a test's fakes otherwise. */
export interface Environment {
  readonly origin: Origin;
  readonly createSocket?: (url: string) => WebSocket;
}

export interface Attachment {
  readonly state: SessionState;
  onState(listener: StateListener): () => void;
  restart(): void;
  /** Takes the code intelligence out of the editor, which tells the server the file is closed;
   * for an editor already destroyed it only forgets the file. */
  detach(): void;
}

interface Attached {
  readonly session: Session;
  readonly uri: string;
  readonly attemptId: number;
  readonly path: string;
}

export class CodeIntelligence {
  readonly #sessions = new Map<string, Session>();
  readonly #attached = new Set<Attached>();
  #hidden: ReturnType<typeof setTimeout> | undefined;
  #suspended = false;

  readonly #environment: Environment | undefined;
  readonly #unfollow: () => void;

  constructor(page: PageHooks, environment?: Environment) {
    this.#environment = environment;
    // The manager outlives the Attempt view, so it hears the preference itself: turning code
    // intelligence off closes every session at once, whatever view is open.
    this.#unfollow = page.onPreferences(() => {
      if (!page.enabled()) this.closeAll();
    });
    document.addEventListener("visibilitychange", this.#onVisibility);
    window.addEventListener(FILE_SAVED_EVENT, this.#onSaved as EventListener);
  }

  attach(request: AttachRequest): Attachment {
    const session = this.#sessionFor(request);
    const uri = fileUri(request.workspace, request.root, request.path);
    const attached: Attached = { session, uri, attemptId: request.attemptId, path: request.path };
    this.#attached.add(attached);
    request.editor.setIntelligence(session.plugin(uri, request.languageId));
    return {
      get state() {
        return session.state;
      },
      onState: (listener) => session.onState(listener),
      restart: () => session.restart(),
      detach: () => {
        this.#attached.delete(attached);
        request.editor.setIntelligence([]);
        request.editor.setLiveDiagnostics([]);
      },
    };
  }

  /** Closes every session at once, as when code intelligence is turned off. */
  closeAll(): void {
    for (const session of this.#sessions.values()) session.close();
    this.#sessions.clear();
    this.#attached.clear();
  }

  /** Closes every session and stops listening to the page. */
  dispose(): void {
    this.closeAll();
    this.#unfollow();
    clearTimeout(this.#hidden);
    document.removeEventListener("visibilitychange", this.#onVisibility);
    window.removeEventListener(FILE_SAVED_EVENT, this.#onSaved as EventListener);
  }

  #sessionFor(request: AttachRequest): Session {
    const key = rootUri(request.workspace, request.root);
    const found = this.#sessions.get(key);
    if (found !== undefined) {
      found.useAttempt(request.attemptId);
      return found;
    }
    const session: Session = new Session({
      attemptId: request.attemptId,
      origin: this.#environment?.origin ?? location,
      ...(this.#environment?.createSocket === undefined ? {} : { createSocket: this.#environment.createSocket }),
      csrf: request.csrf,
      rootUri: key,
      idleMs: request.idleS * SECOND_MS,
      onIdle: () => {
        if (this.#sessions.get(key) === session) this.#sessions.delete(key);
      },
    });
    this.#sessions.set(key, session);
    session.start();
    return session;
  }

  readonly #onVisibility = (): void => {
    if (document.hidden) {
      this.#hidden = setTimeout(() => {
        this.#suspended = true;
        for (const session of this.#sessions.values()) session.suspend();
      }, HIDDEN_CLOSE_MS);
      return;
    }
    clearTimeout(this.#hidden);
    if (!this.#suspended) return;
    this.#suspended = false;
    for (const session of this.#sessions.values()) session.resume();
  };

  readonly #onSaved = (event: CustomEvent<FileSaved>): void => {
    const { attemptId, path } = event.detail;
    for (const attached of this.#attached) {
      if (attached.attemptId === attemptId && attached.path === path) attached.session.saved(attached.uri);
    }
  };
}

let instance: CodeIntelligence | null = null;

/** The page's one set of sessions. */
export function codeIntelligence(page: PageHooks): CodeIntelligence {
  instance ??= new CodeIntelligence(page);
  return instance;
}

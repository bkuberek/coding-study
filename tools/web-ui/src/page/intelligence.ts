/**
 * Code intelligence in the Attempt view's editors (docs/specs/web-ui.md#code-intelligence-in-the-editor):
 * decides, for each file a tab opens, whether a language server serves it, loads the
 * code-intelligence chunk only when one does, hands the editor to the chunk's sessions, and keeps
 * the status bar's segment on the file in front. This module is in the main bundle and stays
 * small: everything that needs `@codemirror/lsp-client` is in the chunk.
 */

import type { Attachment, Navigator } from "../code-intelligence.ts";
import { languageIdFor, serverLanguageFor } from "../code-intelligence/documents.ts";
import type { Editor } from "../editor.ts";
import type { PageContext } from "./context.ts";
import { h } from "./dom.ts";
import type { SessionState } from "./intelligence-state.ts";
import { type FileIntelligence, type Segment, segmentOf } from "./intelligence-status.ts";
import { fetchChunk } from "./lazy.ts";
import { LibraryTabs } from "./library-tabs.ts";
import { autocompleteApplies } from "./preferences.ts";
import type { LanguageState, LanguageStates } from "./types.ts";
import type { EditorTabs } from "./workbench.ts";

const LANGUAGES = "/api/v1/code-intelligence/languages";
const DOCTOR_FIX = "doctor_fix";
const STARTING: SessionState = { kind: "starting" };
/** How long the status bar's segment says what a jump found. */
const NOTICE_MS = 3000;

export type Decision =
  /** The file works as it does without code intelligence. */
  | { readonly kind: "none" }
  /** The file could have a server; the list of languages is not read yet. */
  | { readonly kind: "waiting" }
  | { readonly kind: "show"; readonly found: FileIntelligence }
  | { readonly kind: "attach"; readonly language: string; readonly server: string; readonly idleS: number };

/** The attempt as code intelligence sees it, from its status. */
export interface AttemptLanguage {
  readonly language: string | null;
  /** Why the attempt has none whatever its language's server (`service_project`, in a language whose server runs
   * in no sidecar yet), or null. */
  readonly noCodeIntelligence: string | null;
}

const NO_ATTEMPT: AttemptLanguage = { language: null, noCodeIntelligence: null };

/** What a file gets: a session of its language's server when the attempt is in that language and
 * the server is installed, else the status bar's reason, else nothing. An attempt whose status
 * withholds code intelligence never reads the list nor opens a session. */
export function decide(path: string, attempt: AttemptLanguage, states: readonly LanguageState[] | null): Decision {
  const language = serverLanguageFor(path);
  if (language === null || language !== attempt.language) return { kind: "none" };
  if (attempt.noCodeIntelligence !== null) return { kind: "show", found: { kind: "withheld", reason: attempt.noCodeIntelligence, language } };
  if (states === null) return { kind: "waiting" };
  const state = states.find((candidate) => candidate.language === language);
  if (state === undefined) return { kind: "none" };
  if (state.server === null) return { kind: "show", found: { kind: "no-server", language } };
  if (state.state === "needs_jdk") return { kind: "show", found: { kind: "needs-jdk", language, detail: state.detail } };
  if (state.state === "expired") return { kind: "show", found: { kind: "unusable", language, detail: state.detail } };
  if (state.state === "license_not_accepted") {
    return { kind: "show", found: { kind: "license", language, server: state.server, detail: state.detail } };
  }
  if (state.state !== "installed") return { kind: "show", found: { kind: "not-installed", language, server: state.server } };
  return { kind: "attach", language, server: state.server, idleS: state.idle_s ?? 0 };
}

interface Tracked {
  readonly editor: Editor;
  /** Bumped by every decision, so an answer to an older one is ignored. */
  turn: number;
  found: FileIntelligence | null;
  attachment: Attachment | null;
  unsubscribe: (() => void) | null;
  /** Stops hearing the editor's diagnostics, whose counts the segment shows. */
  readonly stopCounting: () => void;
}

export class IntelligenceLink {
  readonly #context: PageContext;
  readonly #attemptId: number;
  readonly #tabs: EditorTabs;
  readonly #libraries: LibraryTabs;
  readonly #tracked = new Map<string, Tracked>();
  readonly #undo: (() => void)[] = [];
  #attempt: AttemptLanguage = NO_ATTEMPT;
  #root: string | null = null;
  #states: readonly LanguageState[] | null = null;
  #reading: Promise<void> | null = null;
  #active: string | null = null;
  #chunk: Promise<typeof import("../code-intelligence.ts") | null> | null = null;
  #notice: string | null = null;
  #noticeTimer: ReturnType<typeof setTimeout> | undefined;
  #destroyed = false;
  /** The preference as the last change left it, so an unrelated change (the theme) does nothing. */
  #wasEnabled: boolean;

  constructor(context: PageContext, tabs: EditorTabs, attemptId: number) {
    this.#context = context;
    this.#tabs = tabs;
    this.#libraries = new LibraryTabs(tabs, context);
    this.#attemptId = attemptId;
    this.#wasEnabled = context.preferences().code_intelligence;
    this.#undo.push(
      tabs.onEditor((path, editor) => this.#track(path, editor)),
      tabs.onActive((path) => {
        this.#active = path;
        this.#render();
      }),
      tabs.onClosed((path) => {
        this.#untrack(path);
        this.#libraries.closed(path);
      }),
      context.onPreferences((preferences) => this.#libraries.apply(preferences)),
      context.onPreferences(() => this.#preferencesChanged()),
      context.notifications.subscribe((notice) => {
        if (notice.type === "job_ended" && notice.command === DOCTOR_FIX && this.#enabled()) void this.#reread();
      }),
    );
    this.#active = tabs.active;
    for (const [path, editor] of tabs.editors()) this.#track(path, editor);
  }

  /** The attempt's language and its tree's root, which the files' URIs and servers follow from. */
  configure(attempt: AttemptLanguage, root: string): void {
    const same = attempt.language === this.#attempt.language && attempt.noCodeIntelligence === this.#attempt.noCodeIntelligence;
    if (same && root === this.#root) return;
    this.#attempt = attempt;
    this.#root = root;
    this.#considerAll();
  }

  /** Takes the code intelligence out of every editor; the sessions stay for their idle time. */
  destroy(): void {
    this.#destroyed = true;
    clearTimeout(this.#noticeTimer);
    this.#libraries.destroy();
    for (const undo of this.#undo.splice(0)) undo();
    for (const tracked of this.#tracked.values()) {
      this.#release(tracked);
      tracked.stopCounting();
    }
    this.#tracked.clear();
    this.#context.shell.setIntelligence(null);
  }

  #enabled(): boolean {
    return this.#context.preferences().code_intelligence;
  }

  #track(path: string, editor: Editor): void {
    const stopCounting = editor.onDiagnostics(() => {
      if (this.#active === path) this.#render();
    });
    this.#tracked.set(path, { editor, turn: 0, found: null, attachment: null, unsubscribe: null, stopCounting });
    void this.#consider(path);
  }

  #untrack(path: string): void {
    const tracked = this.#tracked.get(path);
    if (tracked === undefined) return;
    tracked.turn += 1;
    this.#release(tracked);
    tracked.stopCounting();
    this.#tracked.delete(path);
    this.#render();
  }

  #preferencesChanged(): void {
    if (this.#enabled() === this.#wasEnabled) return;
    this.#wasEnabled = this.#enabled();
    if (this.#wasEnabled) {
      this.#considerAll();
      return;
    }
    for (const tracked of this.#tracked.values()) {
      tracked.turn += 1;
      this.#release(tracked);
    }
    this.#libraries.release();
    this.#render();
  }

  #considerAll(): void {
    for (const path of this.#tracked.keys()) void this.#consider(path);
  }

  async #consider(path: string): Promise<void> {
    const tracked = this.#tracked.get(path);
    if (tracked === undefined) return;
    const turn = ++tracked.turn;
    if (!this.#enabled() || this.#root === null) {
      this.#release(tracked);
      this.#render();
      return;
    }
    if (decide(path, this.#attempt, this.#states).kind === "waiting") await this.#read();
    if (this.#stale(tracked, turn)) return;
    const decision = decide(path, this.#attempt, this.#states);
    if (decision.kind === "attach") {
      await this.#attach(path, tracked, turn, decision);
      return;
    }
    this.#release(tracked);
    tracked.found = decision.kind === "show" ? decision.found : null;
    this.#render();
  }

  async #attach(path: string, tracked: Tracked, turn: number, decision: Extract<Decision, { kind: "attach" }>): Promise<void> {
    if (tracked.attachment !== null) return;
    const root = this.#root;
    const languageId = languageIdFor(path);
    if (root === null || languageId === null) return;
    tracked.found = { kind: "session", language: decision.language, server: decision.server, state: STARTING };
    this.#render();
    const chunk = await this.#loadChunk();
    if (this.#stale(tracked, turn)) return;
    if (chunk === null) {
      tracked.found = null;
      this.#render();
      return;
    }
    const attachment = chunk
      .codeIntelligence({
        enabled: () => this.#enabled(),
        autocomplete: () => autocompleteApplies(this.#context.preferences()),
        onPreferences: (listener) => this.#context.onPreferences(listener),
      })
      .attach({
      editor: tracked.editor,
      csrf: this.#context.csrf,
      attemptId: this.#attemptId,
      path,
      languageId,
      workspace: this.#context.session.workspace,
      root,
      idleS: decision.idleS,
      announce: (message) => this.#context.shell.announce(message),
      navigator: this.#navigator,
    });
    tracked.attachment = attachment;
    tracked.unsubscribe = attachment.onState(() => this.#render());
    this.#render();
  }

  /** Whether another decision, a closed tab or a preference change came while this one waited. */
  #stale(tracked: Tracked, turn: number): boolean {
    return this.#destroyed || tracked.turn !== turn || !this.#enabled();
  }

  #release(tracked: Tracked): void {
    tracked.unsubscribe?.();
    tracked.attachment?.detach();
    tracked.unsubscribe = null;
    tracked.attachment = null;
    tracked.found = null;
  }

  #read(): Promise<void> {
    this.#reading ??= this.#context.api
      .get<LanguageStates>(LANGUAGES)
      .then((read) => {
        this.#states = read.languages;
      })
      // The files wait; the next preference change or installation reads the list again.
      .catch(() => {})
      .finally(() => {
        this.#reading = null;
      });
    return this.#reading;
  }

  /** After an installation: the list again, then every file once more. */
  async #reread(): Promise<void> {
    await this.#read();
    this.#considerAll();
  }

  #loadChunk(): Promise<typeof import("../code-intelligence.ts") | null> {
    this.#chunk ??= fetchChunk(
      (message) => this.#context.shell.announce(message),
      () => import("../code-intelligence.ts"),
    ).then((module) => {
      if (module === null) this.#chunk = null;
      return module;
    });
    return this.#chunk;
  }

  /** What a jump asks of the page's tabs. */
  readonly #navigator: Navigator = {
    paths: async () => new Set((await this.#tabs.files.tree()).entries.map((entry) => entry.path)),
    openFile: async (path) => {
      await this.#tabs.open(path);
      return this.#tabs.editors().get(path) ?? null;
    },
    openLibrary: async (file) => {
      const chunk = await this.#loadChunk();
      return chunk === null ? null : this.#libraries.open(file, chunk.libraryNavigation(this.#navigator));
    },
    showLibrary: (uri) => this.#libraries.show(uri),
    say: (text) => this.#say(text),
  };

  /** The status bar says what a jump found for a few seconds. */
  #say(text: string): void {
    clearTimeout(this.#noticeTimer);
    this.#notice = text;
    this.#render();
    this.#noticeTimer = setTimeout(() => {
      this.#notice = null;
      this.#render();
    }, NOTICE_MS);
  }

  #render(): void {
    if (this.#destroyed) return;
    const tracked = this.#active === null ? undefined : this.#tracked.get(this.#active);
    const found = tracked === undefined || !this.#enabled() ? null : foundOf(tracked);
    const counts = tracked?.editor.diagnosticCounts;
    const segment = found === null ? null : this.#notice === null ? segmentOf(found, counts) : noticeSegment(this.#notice);
    this.#context.shell.setIntelligence(segment === null ? null : segmentElement(segment, () => tracked?.attachment?.restart()));
  }
}

function noticeSegment(text: string): Segment {
  return { text, action: null, title: "", state: "notice" };
}

function foundOf(tracked: Tracked): FileIntelligence | null {
  const found = tracked.found;
  if (found === null || found.kind !== "session" || tracked.attachment === null) return found;
  return { ...found, state: tracked.attachment.state };
}

/** The status bar segment: its text and, after a dot, its control, Restart or the link to the Health view. */
function segmentElement(segment: Segment, restart: () => void): HTMLElement {
  return h("span", { class: "segment code-intelligence", "data-state": segment.state, title: segment.title || null }, ...content(segment, restart));
}

function content(segment: Segment, restart: () => void): (Node | string)[] {
  if (segment.action === "restart") {
    const button = h("button", { type: "button", class: "segment-action" }, "Restart");
    button.addEventListener("click", restart);
    return [`${segment.text} · `, button];
  }
  if (segment.action === "health") return [`${segment.text} · `, h("a", { class: "segment-action", href: "#/health" }, "Health")];
  return [segment.text];
}

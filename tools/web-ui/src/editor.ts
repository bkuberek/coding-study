/**
 * The code editor of the cstudy web UI (docs/specs/web-ui.md#editor):
 * CodeMirror 6 with a language per file extension, each fetched the first time a file needs it;
 * `cstudy` diagnostics as lint markers; light and dark themes; opt-in Vim keybindings, fetched
 * when first turned on; and a keyboard path out of the editor.
 *
 * Tab indents. Escape, then Tab within two seconds, moves focus out of the editor, as CodeMirror
 * does for an Escape no key binding takes; Ctrl-M (Shift-Alt-M on macOS) toggles tab focus mode,
 * in which Tab always moves focus. With Vim keybindings on, Vim takes Escape in insert mode, and the
 * toggle stays bound above Vim's keys.
 */
import { indentWithTab, isolateHistory, toggleTabFocusMode } from "@codemirror/commands";
import { lintGutter, setDiagnostics } from "@codemirror/lint";
import { Compartment, EditorSelection, EditorState, type Extension, Prec, type Text } from "@codemirror/state";
import { EditorView, keymap, runScopeHandlers } from "@codemirror/view";

import { type FileDiagnostic, lintDiagnostics } from "./diagnostics.ts";
import { loadLanguage } from "./language-loaders.ts";
import { languageForPath } from "./languages.ts";
import { cursorPosition } from "./positions.ts";
import { completion, editorSetup } from "./setup.ts";
import { textChange } from "./text-change.ts";
import { type ThemeName, themeExtension } from "./themes.ts";

export type { FileDiagnostic } from "./diagnostics.ts";
export { type LanguageName, languageForPath } from "./languages.ts";
export type { ThemeName } from "./themes.ts";

/** A theme, or "system" to follow the browser's `prefers-color-scheme`. */
export type ThemePreference = ThemeName | "system";

export interface EditorOptions {
  /** The element the editor is appended to. */
  readonly parent: HTMLElement;
  /** The file's path in the project folder: it picks the language and names the editor for screen readers. */
  readonly path: string;
  readonly text: string;
  /** The page's CSP nonce: CodeMirror adds style elements, which `style-src 'nonce-…'` blocks without it. */
  readonly nonce?: string;
  /** "system" by default. */
  readonly theme?: ThemePreference;
  readonly readOnly?: boolean;
  readonly vim?: boolean;
  /** Whether the `autocomplete` preference applies (`autocompleteApplies`); false by default. */
  readonly autocomplete?: boolean;
}

export type ChangeListener = (editor: Editor) => void;

const DARK_SCHEME = "(prefers-color-scheme: dark)";
const TAB_FOCUS_SCOPE = "cstudy-tab-focus";

// Vim reads keys in a DOM handler that runs before every keymap, so the toggle, the way out of the
// editor with Vim on, runs from a handler placed before Vim's.
const TAB_FOCUS_TOGGLE: Extension = [
  keymap.of([{ key: "Ctrl-m", mac: "Shift-Alt-m", run: toggleTabFocusMode, scope: TAB_FOCUS_SCOPE }]),
  EditorView.domEventHandlers({ keydown: (event, view) => runScopeHandlers(view, event, TAB_FOCUS_SCOPE) }),
];

/** What fills the editor's reconfigurable slots in a new state. */
interface Slots {
  readonly language: Extension;
  readonly vim: Extension;
  readonly theme: Extension;
  readonly readOnly: Extension;
  readonly completion: Extension;
  readonly intelligence: Extension;
}

/** Creates an editor; the promise resolves once the file's language and any Vim keybindings apply. */
export function createEditor(options: EditorOptions): Promise<Editor> {
  return Editor.create(options);
}

export class Editor {
  readonly view: EditorView;
  readonly #language = new Compartment();
  readonly #theme = new Compartment();
  readonly #readOnly = new Compartment();
  readonly #vim = new Compartment();
  readonly #completion = new Compartment();
  readonly #intelligence = new Compartment();
  readonly #nonce: Extension;
  readonly #listeners = new Set<ChangeListener>();
  readonly #systemScheme = window.matchMedia(DARK_SCHEME);
  #themePreference: ThemePreference;
  #path: string;
  #saved: Text;
  // Each request for a language or for Vim supersedes the ones still loading.
  #languageRequest = 0;
  #languageLoad: Promise<void> = Promise.resolve();
  #vimRequest = 0;
  #destroyed = false;

  static async create(options: EditorOptions): Promise<Editor> {
    const editor = new Editor(options);
    editor.#languageLoad = editor.#loadLanguage(options.path);
    await Promise.all([editor.#languageLoad, editor.setVim(options.vim ?? false)]);
    return editor;
  }

  private constructor(options: EditorOptions) {
    this.#nonce = options.nonce ? EditorView.cspNonce.of(options.nonce) : [];
    this.#themePreference = options.theme ?? "system";
    this.#path = options.path;
    const state = this.#state(options.path, options.text, {
      language: [],
      vim: [],
      theme: themeExtension(this.#themeName()),
      readOnly: readOnlyExtension(options.readOnly ?? false),
      completion: completion(options.autocomplete ?? false),
      intelligence: [],
    });
    this.#saved = state.doc;
    this.view = new EditorView({ parent: options.parent, state });
    this.#systemScheme.addEventListener("change", this.#followSystemScheme);
  }

  get path(): string {
    return this.#path;
  }

  get text(): string {
    return this.view.state.doc.toString();
  }

  /** Whether the text differs from the text last set or marked saved. */
  get modified(): boolean {
    return !this.view.state.doc.eq(this.#saved);
  }

  /**
   * Shows another file, with fresh undo history and no diagnostics. Its text shows at once; the
   * promise resolves once its language highlights it, and rejects if the language's chunk fails to
   * load, leaving the text unhighlighted.
   */
  async setDocument(path: string, text: string): Promise<void> {
    const current = this.view.state;
    const sameLanguage = languageForPath(path) === languageForPath(this.#path);
    const state = this.#state(path, text, {
      language: sameLanguage ? (this.#language.get(current) ?? []) : [],
      vim: this.#vim.get(current) ?? [],
      theme: this.#theme.get(current) ?? [],
      readOnly: this.#readOnly.get(current) ?? [],
      completion: this.#completion.get(current) ?? [],
      // Bound to the file it was made for.
      intelligence: [],
    });
    this.#path = path;
    this.#saved = state.doc;
    this.view.setState(state);
    if (!sameLanguage) this.#languageLoad = this.#loadLanguage(path);
    await this.#languageLoad;
  }

  /**
   * Shows `text` in place of the editor's, as a file's new version on disk: only what differs
   * changes, so the cursor, the selection and the scroll position stay where the text around them
   * did, and the change is one step that undo takes back. Diagnostics stay; the text is not marked
   * saved.
   */
  replaceText(text: string): void {
    const change = textChange(this.text, text);
    if (change !== null) this.view.dispatch({ changes: change, annotations: isolateHistory.of("full") });
  }

  /** Records the current text as saved, so `modified` turns false until the next change. */
  markSaved(): void {
    this.#saved = this.view.state.doc;
  }

  /** Calls the listener after every change to the text; the function returned removes it. */
  onChange(listener: ChangeListener): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  /** Replaces the lint markers with the diagnostics of this file. */
  setDiagnostics(diagnostics: readonly FileDiagnostic[]): void {
    const state = this.view.state;
    this.view.dispatch(setDiagnostics(state, lintDiagnostics(state.doc, diagnostics)));
  }

  /** Moves the cursor to a 1-based line and column, scrolls it into view and focuses the editor. */
  jumpTo(line: number, column: number | null = null): void {
    const position = cursorPosition(this.view.state.doc, line, column);
    this.view.dispatch({
      selection: EditorSelection.cursor(position),
      effects: EditorView.scrollIntoView(position, { y: "center" }),
    });
    this.view.focus();
  }

  setReadOnly(readOnly: boolean): void {
    this.#reconfigure(this.#readOnly, readOnlyExtension(readOnly));
  }

  setTheme(preference: ThemePreference): void {
    this.#themePreference = preference;
    this.#reconfigure(this.#theme, themeExtension(this.#themeName()));
  }

  /** Turns CodeMirror's completion on or off with the `autocomplete` preference. */
  setAutocomplete(applies: boolean): void {
    this.#reconfigure(this.#completion, completion(applies));
  }

  /**
   * Puts a code-intelligence session's extension in the editor, or takes it out with `[]`
   * (docs/specs/web-ui.md#code-intelligence-in-the-editor). The extension is made for this file's
   * URI, so a new document starts without one. An editor already destroyed ignores the call.
   */
  setIntelligence(extension: Extension): void {
    if (!this.#destroyed) this.#reconfigure(this.#intelligence, extension);
  }

  /** Turns Vim keybindings on or off; the first time on fetches their chunk. */
  async setVim(enabled: boolean): Promise<void> {
    const request = ++this.#vimRequest;
    const extension = enabled ? (await import("./vim.ts")).vimKeybindings() : [];
    if (request === this.#vimRequest) this.#reconfigure(this.#vim, extension);
  }

  focus(): void {
    this.view.focus();
  }

  destroy(): void {
    this.#destroyed = true;
    this.#systemScheme.removeEventListener("change", this.#followSystemScheme);
    this.#listeners.clear();
    this.view.destroy();
  }

  #state(path: string, text: string, slots: Slots): EditorState {
    return EditorState.create({
      doc: text,
      extensions: [
        this.#nonce,
        Prec.highest(TAB_FOCUS_TOGGLE),
        // Vim's keys must come before every other key binding.
        Prec.highest(this.#vim.of(slots.vim)),
        editorSetup,
        this.#completion.of(slots.completion),
        this.#intelligence.of(slots.intelligence),
        keymap.of([indentWithTab]),
        lintGutter(),
        this.#language.of(slots.language),
        this.#theme.of(slots.theme),
        this.#readOnly.of(slots.readOnly),
        // A tabindex as well as contenteditable, so checkers count the scroller's content focusable.
        EditorView.contentAttributes.of({ "aria-label": path, tabindex: "0" }),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) for (const listener of this.#listeners) listener(this);
        }),
      ],
    });
  }

  async #loadLanguage(path: string): Promise<void> {
    const request = ++this.#languageRequest;
    const name = languageForPath(path);
    const support = name === null ? [] : await loadLanguage(name);
    if (request === this.#languageRequest) this.#reconfigure(this.#language, support);
  }

  #reconfigure(compartment: Compartment, extension: Extension): void {
    this.view.dispatch({ effects: compartment.reconfigure(extension) });
  }

  #themeName(): ThemeName {
    if (this.#themePreference !== "system") return this.#themePreference;
    return this.#systemScheme.matches ? "dark" : "light";
  }

  readonly #followSystemScheme = (): void => {
    if (this.#themePreference === "system") this.#reconfigure(this.#theme, themeExtension(this.#themeName()));
  };
}

function readOnlyExtension(readOnly: boolean): Extension {
  // The content stays focusable and selectable, so a screen reader can still read it.
  return readOnly ? [EditorState.readOnly.of(true), EditorView.contentAttributes.of({ "aria-readonly": "true" })] : [];
}

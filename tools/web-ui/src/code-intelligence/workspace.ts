/**
 * The files a session has open (docs/specs/web-ui.md#code-intelligence-in-the-editor): the tabs'
 * documents, with their unsaved edits. `LSPClient`'s default workspace is not exported; this one
 * does the same for one view per file and tells the session when its first file opens and its
 * last one closes.
 */

import { type LSPClient, LSPPlugin, Workspace, type WorkspaceFile } from "@codemirror/lsp-client";
import type { Text } from "@codemirror/state";
import type { EditorView } from "@codemirror/view";

import { pullAgain, pullDiagnostics } from "./pull.ts";

class SessionFile implements WorkspaceFile {
  readonly uri: string;
  readonly languageId: string;
  version: number;
  doc: Text;
  readonly view: EditorView;

  constructor(uri: string, languageId: string, version: number, doc: Text, view: EditorView) {
    this.uri = uri;
    this.languageId = languageId;
    this.version = version;
    this.doc = doc;
    this.view = view;
  }

  getView(): EditorView {
    return this.view;
  }
}

export class SessionWorkspace extends Workspace {
  files: SessionFile[] = [];
  readonly #versions = new Map<string, number>();
  readonly #filesChanged: (count: number) => void;

  constructor(client: LSPClient, filesChanged: (count: number) => void) {
    super(client);
    this.#filesChanged = filesChanged;
  }

  syncFiles(): ReturnType<Workspace["syncFiles"]> {
    const updates: ReturnType<Workspace["syncFiles"]> extends readonly (infer Update)[] ? Update[] : never = [];
    for (const file of this.files) {
      const plugin = LSPPlugin.get(file.view);
      if (plugin === null || plugin.unsyncedChanges.empty) continue;
      updates.push({ changes: plugin.unsyncedChanges, file, prevDoc: file.doc });
      file.doc = file.view.state.doc;
      file.version = this.#nextVersion(file.uri);
      plugin.clear();
    }
    return updates;
  }

  openFile(uri: string, languageId: string, view: EditorView): void {
    if (this.#find(uri) !== undefined) this.#remove(uri);
    const file = new SessionFile(uri, languageId, this.#nextVersion(uri), view.state.doc, view);
    this.files.push(file);
    this.client.didOpen(file);
    pullDiagnostics(this.client, uri);
    this.#filesChanged(this.files.length);
  }

  closeFile(uri: string, view: EditorView): void {
    const file = this.#find(uri);
    // A view that was replaced by another for the same file no longer owns it.
    if (file === undefined || file.view !== view) return;
    this.#remove(uri);
    this.#filesChanged(this.files.length);
  }

  /** Opens every file again with its text now, as each new connection must, and pulls its diagnostics. */
  override connected(): void {
    for (const file of this.files) {
      file.doc = file.view.state.doc;
      file.version = this.#nextVersion(file.uri);
      LSPPlugin.get(file.view)?.clear();
    }
    super.connected();
    pullAgain(this.client);
  }

  /** The number of the files open. */
  get count(): number {
    return this.files.length;
  }

  #find(uri: string): SessionFile | undefined {
    return this.files.find((file) => file.uri === uri);
  }

  #remove(uri: string): void {
    this.files = this.files.filter((file) => file.uri !== uri);
    this.client.didClose(uri);
  }

  #nextVersion(uri: string): number {
    const version = (this.#versions.get(uri) ?? -1) + 1;
    this.#versions.set(uri, version);
    return version;
  }
}

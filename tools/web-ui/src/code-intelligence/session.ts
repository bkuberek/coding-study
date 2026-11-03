/**
 * One code-intelligence session (docs/specs/web-ui.md#sessions): a socket to one language server
 * for one root, and the client on it. It sends the CSRF token first, initializes, and says what
 * state it is in; a socket that closes is tried again or stops as the close code says, Restart
 * and Resume open it again, and a session whose files have all been closed for the language's
 * idle time closes itself.
 */

import type { Extension } from "@codemirror/state";
import { EditorView } from "@codemirror/view";

import { closeOutcome, retryDelay, type SessionState } from "../page/intelligence-state.ts";
import { ServerClient } from "./client.ts";
import { publishDiagnostics } from "./publish.ts";
import { type Origin, SocketTransport, sessionUrl } from "./transport.ts";
import { SessionWorkspace } from "./workspace.ts";

/** `didChange` goes out this long after the last change, and before every request. */
export const SYNC_DELAY_MS = 500;
/** How long a request may take, `initialize` included; the client's own 3 s is too short for a server starting. */
export const REQUEST_TIMEOUT_MS = 15_000;
const NORMAL_CLOSE = 1000;

export type StateListener = (state: SessionState) => void;

export interface SessionOptions {
  /** The attempt the first socket asks for; `useAttempt` changes it. */
  readonly attemptId: number;
  readonly origin: Origin;
  readonly csrf: string;
  readonly rootUri: string;
  /** How long the session lives once its last file is closed. */
  readonly idleMs: number;
  /** Called after the session closed itself for being idle. */
  readonly onIdle: () => void;
  readonly createSocket?: (url: string) => WebSocket;
}

export class Session {
  readonly client: ServerClient;
  readonly #options: SessionOptions;
  readonly #listeners = new Set<StateListener>();
  #state: SessionState = { kind: "starting" };
  #attemptId: number;
  #socket: WebSocket | null = null;
  /** Failures in a row since the session was last ready. */
  #failures = 0;
  #retry: ReturnType<typeof setTimeout> | undefined;
  #idle: ReturnType<typeof setTimeout> | undefined;
  #sync: ReturnType<typeof setTimeout> | undefined;
  /** Whether the client is connected to a socket, so there is something to sync. */
  #linked = false;
  #suspended = false;
  #closed = false;

  constructor(options: SessionOptions) {
    this.#options = options;
    this.#attemptId = options.attemptId;
    this.client = new ServerClient({
      rootUri: options.rootUri,
      timeout: REQUEST_TIMEOUT_MS,
      notificationHandlers: { "textDocument/publishDiagnostics": publishDiagnostics },
      workspace: (client) => new SessionWorkspace(client, (count) => this.filesChanged(count)),
      extensions: [{ editorExtension: EditorView.updateListener.of((update) => update.docChanged && this.#scheduleSync()) }],
    });
  }

  get state(): SessionState {
    return this.#state;
  }

  /** The URI of the session's root, which the URIs of its files are under. */
  get rootUri(): string {
    return this.#options.rootUri;
  }

  /** Calls the listener after each change of state; the function returned removes it. */
  onState(listener: StateListener): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  /** The extension that opens a file of this session in an editor, and closes it with the editor. */
  plugin(uri: string, languageId: string): Extension {
    return this.client.plugin(uri, languageId);
  }

  get fileCount(): number {
    return (this.client.workspace as SessionWorkspace).count;
  }

  /** A later attempt in the same root reuses the session, and its next socket asks for that one. */
  useAttempt(attemptId: number): void {
    this.#attemptId = attemptId;
  }

  start(): void {
    this.#open();
  }

  /** Opens the session again with fresh tries, as after it stopped. */
  restart(): void {
    if (this.#closed) return;
    this.#suspended = false;
    this.#drop();
    this.#failures = 0;
    this.#open();
  }

  /** Closes the socket of a hidden tab, keeping the files; `resume` opens it again. */
  suspend(): void {
    if (this.#closed || this.#suspended) return;
    this.#suspended = true;
    this.#drop();
  }

  resume(): void {
    if (this.#closed || !this.#suspended) return;
    this.#suspended = false;
    this.#failures = 0;
    this.#open();
  }

  /** Ends the session: the socket closes with 1000 and nothing opens it again. */
  close(): void {
    this.#closed = true;
    clearTimeout(this.#idle);
    clearTimeout(this.#sync);
    this.#drop();
  }

  /** The workspace calls this when a file opens or closes. */
  filesChanged(count: number): void {
    clearTimeout(this.#idle);
    if (count === 0 && !this.#closed) {
      this.#idle = setTimeout(() => {
        this.close();
        this.#options.onIdle();
      }, this.#options.idleMs);
    }
  }

  /** Tells the server the file was saved, after the changes it saved. */
  saved(uri: string): void {
    this.client.sync();
    this.client.notification("textDocument/didSave", { textDocument: { uri } });
  }

  #open(): void {
    this.#setState(this.#failures === 0 ? { kind: "starting" } : { kind: "reconnecting" });
    let socket: WebSocket;
    try {
      socket = (this.#options.createSocket ?? ((url) => new WebSocket(url)))(sessionUrl(this.#options.origin, this.#attemptId));
    } catch (error) {
      this.#setState({ kind: "stopped", why: "cannot connect", reason: error instanceof Error ? error.message : String(error) });
      return;
    }
    this.#socket = socket;
    const transport = new SocketTransport(socket);
    socket.addEventListener("open", () => this.#opened(socket, transport));
    socket.addEventListener("message", (event) => {
      if (socket === this.#socket && typeof event.data === "string") transport.deliver(event.data);
    });
    socket.addEventListener("close", (event) => this.#closedByPeer(socket, event.code, event.reason));
  }

  #opened(socket: WebSocket, transport: SocketTransport): void {
    if (socket !== this.#socket) return;
    socket.send(JSON.stringify({ csrf: this.#options.csrf }));
    this.#linked = true;
    this.client.connect(transport);
    this.client.initializing.then(
      () => {
        if (socket !== this.#socket) return;
        this.#failures = 0;
        this.#setState({ kind: "ready" });
      },
      (error: unknown) => {
        if (socket !== this.#socket) return;
        this.#drop();
        this.#setState({ kind: "stopped", why: "no answer", reason: error instanceof Error ? error.message : String(error) });
      },
    );
  }

  #closedByPeer(socket: WebSocket, code: number, reason: string): void {
    if (socket !== this.#socket) return;
    this.#socket = null;
    this.#unlink();
    const outcome = closeOutcome(code, reason);
    if (outcome.kind === "stopped") {
      this.#setState(outcome);
    } else if (outcome.kind === "gone") {
      this.#setState({ kind: "stopped", why: "", reason });
    } else {
      this.#tryAgain();
    }
  }

  #tryAgain(): void {
    const delay = retryDelay(this.#failures);
    if (delay === null) {
      this.#setState({ kind: "stopped", why: "", reason: "" });
      return;
    }
    this.#failures += 1;
    this.#setState({ kind: "reconnecting" });
    this.#retry = setTimeout(() => this.#open(), delay);
  }

  /** Closes the socket the page owns, if any, and forgets the pending try. */
  #drop(): void {
    clearTimeout(this.#retry);
    const socket = this.#socket;
    this.#socket = null;
    if (socket !== null) socket.close(NORMAL_CLOSE);
    this.#unlink();
  }

  #unlink(): void {
    if (this.#linked) this.client.disconnect();
    this.#linked = false;
  }

  #scheduleSync(): void {
    clearTimeout(this.#sync);
    this.#sync = setTimeout(() => {
      if (this.#linked) this.client.sync();
    }, SYNC_DELAY_MS);
  }

  #setState(state: SessionState): void {
    const same = state.kind === this.#state.kind && (state.kind !== "stopped" || (this.#state.kind === "stopped" && state.why === this.#state.why && state.reason === this.#state.reason));
    if (same) return;
    this.#state = state;
    for (const listener of this.#listeners) listener(state);
  }
}

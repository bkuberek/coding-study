/** A WebSocket as the session tests see it: the part the session uses, and the server's side of it. */

const OPEN = 1;
const CLOSED = 3;

/** The part of a WebSocket the session uses. */
export class FakeSocket extends EventTarget {
  readyState = 0;
  readonly sent: string[] = [];
  #closedWith: number | null = null;

  readonly url: string;

  constructor(url: string) {
    super();
    this.url = url;
  }

  send(text: string): void {
    this.sent.push(text);
  }

  close(code = 1005, reason = ""): void {
    void reason;
    this.#closedWith = code;
    this.readyState = CLOSED;
  }

  /** The code the page closed the socket with, or null while it did not. */
  closeCode(): number | null {
    return this.#closedWith;
  }

  accept(): void {
    this.readyState = OPEN;
    this.dispatchEvent(new Event("open"));
  }

  receive(message: unknown): void {
    this.dispatchEvent(Object.assign(new Event("message"), { data: JSON.stringify(message) }));
  }

  drop(code: number, reason = ""): void {
    this.readyState = CLOSED;
    this.dispatchEvent(Object.assign(new Event("close"), { code, reason }));
  }

  messages(): { id?: number; method?: string }[] {
    return this.sent.map((text) => JSON.parse(text));
  }
}

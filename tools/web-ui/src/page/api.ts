/**
 * Requests to the API (docs/specs/web-ui.md#api-conventions): JSON in and out, the session
 * cookie sent by the browser, and the page's CSRF token on every write.
 */

export const CSRF_HEADER = "X-Cstudy-CSRF";

/** The API's error document as an exception: `code` such as `usage` or `not_found`. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  /** The CLI's `fix:` hint, for an `environment` error that has one. */
  readonly fix: string | null;
  /** The whole error document, with the fields some errors add, such as a 412's `sha256` or `run` for a taken slot. */
  readonly details: Readonly<Record<string, unknown>>;

  constructor(status: number, code: string, message: string, fix: string | null = null, details: Readonly<Record<string, unknown>> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fix = fix;
    this.details = details;
  }
}

export type Fetch = (input: string, init?: RequestInit) => Promise<Response>;

export type WriteMethod = "POST" | "PUT" | "DELETE";

export interface WriteOptions {
  readonly body?: unknown;
  /** Such as `If-Match`. */
  readonly headers?: Readonly<Record<string, string>>;
}

export interface Api {
  get<Document>(path: string): Promise<Document>;
  put<Document>(path: string, body: unknown): Promise<Document>;
  /** Any write; null for an answer without a body, such as 204. */
  send<Document>(method: WriteMethod, path: string, options?: WriteOptions): Promise<Document | null>;
  post<Document>(path: string, body: unknown): Promise<Document>;
}

/**
 * Dispatched on the page after a file of an attempt was written, by whatever part of the page wrote
 * it, so run on save hears every save (docs/specs/web-ui.md#attempt-view).
 */
export const FILE_SAVED_EVENT = "cstudy:file-saved";

export interface FileSaved {
  readonly attemptId: number;
  /** The file's path in the attempt's tree. */
  readonly path: string;
}

const ATTEMPT_FILE = /^\/api\/v1\/attempts\/(\d+)\/files\/(.+)$/;

export function createApi(
  csrf: string,
  fetcher: Fetch = (input, init) => fetch(input, init),
  events: EventTarget | null = typeof window === "undefined" ? null : window,
): Api {
  async function request<Document>(path: string, init: RequestInit): Promise<Document> {
    const response = await fetcher(path, { ...init, credentials: "same-origin" });
    const body = await response.text();
    if (!response.ok) throw errorOf(response.status, body);
    if (init.method === "PUT") announceSave(path);
    return (body === "" ? null : JSON.parse(body)) as Document;
  }
  /** Every successful PUT of an attempt's file is a save, whether it came through `put` or `send`. */
  function announceSave(path: string): void {
    const found = ATTEMPT_FILE.exec(path);
    if (!found || !events) return;
    const saved: FileSaved = { attemptId: Number(found[1]), path: (found[2] ?? "").split("/").map(decodeURIComponent).join("/") };
    events.dispatchEvent(new CustomEvent(FILE_SAVED_EVENT, { detail: saved }));
  }
  const writeHeaders = { "Content-Type": "application/json", Accept: "application/json", [CSRF_HEADER]: csrf };
  return {
    get: (path) => request(path, { headers: { Accept: "application/json" } }),
    put: (path, body) => request(path, { method: "PUT", headers: writeHeaders, body: JSON.stringify(body) }),
    post: (path, body) => request(path, { method: "POST", headers: writeHeaders, body: JSON.stringify(body) }),
    send: (method, path, options = {}) =>
      request(path, {
        method,
        headers: { ...writeHeaders, ...options.headers },
        ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
      }),
  };
}

/** The error a failed response carries, or one describing it when its body is not the document. */
export function errorOf(status: number, body: string): ApiError {
  try {
    const { error } = JSON.parse(body) as { error?: { code?: unknown; message?: unknown; fix?: unknown } };
    if (error && typeof error.code === "string" && typeof error.message === "string") {
      const fix = typeof error.fix === "string" ? error.fix : null;
      return new ApiError(status, error.code, error.message, fix, error);
    }
  } catch {
    // Not JSON: a proxy or a crash answered instead of the server's error document.
  }
  return new ApiError(status, "internal", `the server answered ${status}`);
}

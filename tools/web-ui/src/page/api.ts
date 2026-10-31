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
  /** The error document's other fields, such as a 412's `sha256`. */
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
}

export function createApi(csrf: string, fetcher: Fetch = (input, init) => fetch(input, init)): Api {
  async function request<Document>(path: string, init: RequestInit): Promise<Document> {
    const response = await fetcher(path, { ...init, credentials: "same-origin" });
    const body = await response.text();
    if (!response.ok) throw errorOf(response.status, body);
    return (body === "" ? null : JSON.parse(body)) as Document;
  }
  const writeHeaders = { "Content-Type": "application/json", Accept: "application/json", [CSRF_HEADER]: csrf };
  return {
    get: (path) => request(path, { headers: { Accept: "application/json" } }),
    put: (path, body) => request(path, { method: "PUT", headers: writeHeaders, body: JSON.stringify(body) }),
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

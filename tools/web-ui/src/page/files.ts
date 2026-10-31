/**
 * The files of an attempt in progress, as the API reads and changes them
 * (docs/specs/web-ui.md#file-api-rules). A save, a move and a delete name the `ETag` the file was
 * read with, and a new file asks for no file at its path, so a change made elsewhere since the
 * read is never lost unseen: the server answers 412, which `conflictOf` reads.
 */

import { type Api, ApiError, type WriteOptions } from "./api.ts";
import type { FileDocument, Tree } from "./types.ts";

export interface SavedFile {
  readonly path: string;
  /** The SHA-256 of the content now on disk: the file's next `ETag`. */
  readonly sha256: string;
}

export interface RestoredFile {
  readonly path: string;
  readonly origin: string;
  readonly level: number | null;
}

/** A change the file no longer allows: it changed or went since the page read it. */
export interface Conflict {
  /** The SHA-256 of the file on disk now; null when it is gone. */
  readonly theirs: string | null;
  readonly message: string;
}

const PRECONDITION_FAILED = "precondition_failed";

/** The conflict a refused change reports; null for any other error. */
export function conflictOf(error: unknown): Conflict | null {
  if (!(error instanceof ApiError) || error.code !== PRECONDITION_FAILED) return null;
  const theirs = error.details["sha256"];
  return { theirs: typeof theirs === "string" ? theirs : null, message: error.message };
}

export function fileUrl(attemptId: number, path: string): string {
  return `/api/v1/attempts/${attemptId}/files/${path.split("/").map(encodeURIComponent).join("/")}`;
}

function ifMatch(sha256: string): Readonly<Record<string, string>> {
  return { "If-Match": `"${sha256}"` };
}

export class AttemptFiles {
  readonly #api: Api;
  readonly #attemptId: number;

  constructor(api: Api, attemptId: number) {
    this.#api = api;
    this.#attemptId = attemptId;
  }

  tree(): Promise<Tree> {
    return this.#api.get(`/api/v1/attempts/${this.#attemptId}/files`);
  }

  read(path: string): Promise<FileDocument> {
    return this.#api.get(fileUrl(this.#attemptId, path));
  }

  /** Writes `text` over the file while it still has the SHA-256 `sha256`. */
  save(path: string, text: string, sha256: string): Promise<SavedFile> {
    return this.#write("PUT", fileUrl(this.#attemptId, path), { body: { text }, headers: ifMatch(sha256) });
  }

  /** Writes a new file, making the folders on the way; refused when a file is there. */
  create(path: string, text: string): Promise<SavedFile> {
    return this.#write("PUT", fileUrl(this.#attemptId, path), { body: { text }, headers: { "If-None-Match": "*" } });
  }

  move(path: string, to: string, sha256: string): Promise<SavedFile> {
    return this.#write("POST", `${fileUrl(this.#attemptId, path)}/move`, { body: { to }, headers: ifMatch(sha256) });
  }

  async remove(path: string, sha256: string): Promise<void> {
    await this.#api.send("DELETE", fileUrl(this.#attemptId, path), { headers: ifMatch(sha256) });
  }

  /** `cstudy start --restore`: a starter or generated test file, as `cstudy` provides it now. */
  restore(path: string): Promise<RestoredFile> {
    return this.#write("POST", `/api/v1/attempts/${this.#attemptId}/restore`, { body: { path } });
  }

  async #write<Document>(method: "POST" | "PUT", path: string, options: WriteOptions): Promise<Document> {
    const document = await this.#api.send<Document>(method, path, options);
    if (document === null) throw new ApiError(500, "internal", `the server answered ${method} ${path} without a document`);
    return document;
  }
}

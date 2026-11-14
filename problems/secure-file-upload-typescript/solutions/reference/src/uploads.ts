// An upload, checked in the statement's order: the request, the name, what the bytes are, the
// quota, and last the scan. The size was checked while the body arrived.

import { createHash } from "node:crypto";

import { jsonObject, refusal } from "./http.ts";
import type { Answer } from "./http.ts";
import { displayName, extensionOf } from "./names.ts";
import type { Quarantine } from "./quarantine.ts";
import { hasActiveContent, sniff } from "./sniffing.ts";
import type { FileStore, StoredFile } from "./store.ts";

/** Standard base64, padded: anything a decoder would skip or guess at is refused instead. */
const BASE64 = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;

export function metadata(file: StoredFile): Record<string, unknown> {
  return { id: file.id, name: file.name, size: file.size, sha256: file.sha256 };
}

export class Uploads {
  readonly #store: FileStore;
  readonly #quarantine: Quarantine;

  constructor(store: FileStore, quarantine: Quarantine) {
    this.#store = store;
    this.#quarantine = quarantine;
  }

  async receive(owner: string, body: Buffer): Promise<Answer> {
    const fields = jsonObject(body);
    const data = fields?.data;
    if (typeof fields?.name !== "string" || typeof data !== "string" || !BASE64.test(data)) {
      return refusal(400, "invalid_request");
    }
    const bytes = Buffer.from(data, "base64");
    if (bytes.length === 0) {
      return refusal(400, "invalid_request");
    }
    const name = displayName(fields.name);
    if (name === null) {
      return refusal(400, "invalid_name");
    }
    // The client's content_type is never read: it says what the client hopes, not what this is.
    const type = sniff(bytes);
    if (type === undefined) {
      return refusal(415, "unsupported_type");
    }
    if (!type.extensions.includes(extensionOf(name))) {
      return refusal(415, "type_mismatch");
    }
    if (hasActiveContent(bytes, type)) {
      return refusal(415, "active_content");
    }
    const sha256 = createHash("sha256").update(bytes).digest("hex");
    const file = this.#store.reserve({
      owner,
      name,
      size: bytes.length,
      sha256,
      mime: type.mime,
      inline: type.inline,
    });
    if (file === null) {
      return refusal(507, "quota_exceeded");
    }
    await this.#store.quarantine(file, bytes);
    const verdict = await this.#quarantine.admit(file, bytes);
    if (verdict === "infected") {
      return refusal(422, "infected");
    }
    return { status: verdict === "clean" ? 201 : 202, body: metadata(file) };
  }
}

// Serving a file back. Only a clean file is served, and always with the type its bytes proved, so
// a browser has nothing left to guess.

import { refusal } from "./http.ts";
import type { Answer } from "./http.ts";
import type { FileStore, StoredFile } from "./store.ts";

export function servingHeaders(file: StoredFile): Record<string, string> {
  const disposition = file.inline ? "inline" : "attachment";
  return {
    "Content-Type": file.mime,
    "X-Content-Type-Options": "nosniff",
    "Content-Disposition": `${disposition}; filename="${file.name}"`,
  };
}

export async function content(store: FileStore, file: StoredFile): Promise<Answer> {
  if (file.status === "pending") {
    return refusal(409, "scan_pending");
  }
  if (file.status === "infected") {
    return refusal(410, "infected");
  }
  return { status: 200, bytes: await store.released(file), headers: servingHeaders(file) };
}

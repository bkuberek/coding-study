// The team's shared files, kept in attachments/ and downloaded by name.

import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

import { notFound } from "./http.ts";
import type { Answer } from "./http.ts";

const folder = resolve("attachments");

function decoded(rawName: string): string {
  try {
    return decodeURIComponent(rawName);
  } catch {
    throw notFound();
  }
}

// The name is decoded first and checked after, on the path it resolves to: a file directly inside
// the folder, and nothing else, however the name was written.
export async function download(rawName: string): Promise<Answer> {
  const path = resolve(folder, decoded(rawName));
  if (dirname(path) !== folder) {
    throw notFound();
  }
  try {
    return { status: 200, bytes: await readFile(path) };
  } catch {
    throw notFound();
  }
}

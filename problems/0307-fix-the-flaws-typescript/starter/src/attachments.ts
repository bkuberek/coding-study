// The team's shared files, kept in attachments/ and downloaded by name.

import { readFile } from "node:fs/promises";
import { join, resolve } from "node:path";

import { notFound } from "./http.ts";
import type { Answer } from "./http.ts";

const folder = resolve("attachments");

export async function download(rawName: string): Promise<Answer> {
  const name = decodeURIComponent(rawName);
  try {
    return { status: 200, bytes: await readFile(join(folder, name)) };
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      throw notFound();
    }
    throw error;
  }
}

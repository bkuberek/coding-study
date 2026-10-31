/**
 * What the page may do with each file of an attempt (docs/specs/web-ui.md#file-scope): a project
 * folder takes new files and folders, moves, deletes and restores; a Java, Kotlin or Go package
 * takes files directly in it with its extension; any other attempt has its one file. The server
 * refuses the rest anyway; these rules only keep the page from offering it.
 */

import type { TreeEntry } from "./types.ts";

export type FileScope = "project" | "package" | "single";

/** The languages whose single-file problems keep a package of files, by their extension. */
const PACKAGE_EXTENSIONS: Readonly<Record<string, string>> = { java: ".java", kotlin: ".kt", go: ".go" };
const PROVIDED_ORIGINS = new Set(["starter", "level"]);
const RESTORABLE_STATES = new Set(["modified", "deleted"]);
const SEPARATOR = "/";

export interface AttemptShape {
  readonly kind: string;
  readonly language: string | null;
}

export interface FileActions {
  readonly rename: boolean;
  readonly delete: boolean;
  /** `cstudy start --restore`: a starter or generated test file that changed or went. */
  readonly restore: boolean;
}

export function fileScope(attempt: AttemptShape): FileScope {
  if (attempt.kind === "project") return "project";
  return packageExtension(attempt) === null ? "single" : "package";
}

/** `.java`, `.kt` or `.go` for a package's files; null for other attempts. */
export function packageExtension(attempt: AttemptShape): string | null {
  if (attempt.kind === "project" || attempt.language === null) return null;
  return PACKAGE_EXTENSIONS[attempt.language] ?? null;
}

export function creates(scope: FileScope): { readonly files: boolean; readonly folders: boolean } {
  return { files: scope !== "single", folders: scope === "project" };
}

export function fileActions(scope: FileScope, entry: Pick<TreeEntry, "origin" | "state" | "size">): FileActions {
  const reshapes = scope !== "single" && entry.size !== null;
  const restorable = PROVIDED_ORIGINS.has(entry.origin) && RESTORABLE_STATES.has(entry.state ?? "");
  return { rename: reshapes, delete: reshapes, restore: scope === "project" && restorable };
}

/** Why `name` cannot name a file or folder relative to a folder of the attempt; null when it can. */
export function nameIssue(scope: FileScope, extension: string | null, name: string): string | null {
  if (name.trim() === "") return "type a name";
  if (name.startsWith(SEPARATOR)) return "a name is relative to its folder";
  if (name.includes("\\")) return "use / between folders, not \\";
  if (name.split(SEPARATOR).some((segment) => segment === "" || segment === "." || segment === "..")) {
    return "no . or .. or empty folder in a name";
  }
  if (scope !== "package") return null;
  if (name.includes(SEPARATOR)) return "a file of this package goes directly in it";
  return extension !== null && !name.endsWith(extension) ? `end the name with ${extension}` : null;
}

export function joinPath(folder: string, name: string): string {
  return folder === "" ? name : `${folder}${SEPARATOR}${name}`;
}

/** The folder a path lies in, relative to the attempt's root; "" at the root. */
export function parentOf(path: string): string {
  const at = path.lastIndexOf(SEPARATOR);
  return at < 0 ? "" : path.slice(0, at);
}

export function baseName(path: string): string {
  return path.slice(path.lastIndexOf(SEPARATOR) + 1);
}

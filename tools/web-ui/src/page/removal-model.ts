/**
 * What the removal dialog says of the languages Save would take out of the workspace
 * (docs/specs/web-ui.md#settings-view): its title and command, the folders each language owns and
 * the preview `GET /api/v1/languages/removal` answers, in the words of `cstudy lang remove`.
 */

/** `GET /api/v1/languages/removal`: what a deletion of the folders would delete, keep and leave. */
export interface RemovalPreview {
  readonly delete: readonly { readonly path: string; readonly files: number }[];
  readonly keep: readonly { readonly path: string; readonly reason: string }[];
  readonly stays: readonly string[];
  /** The CLI's refusal for each attempt in progress in those languages. */
  readonly blocked: readonly string[];
}

/** The folder each language practices in, as `cstudy lang` names it: Java and Kotlin share
 * `jvm/`, and Go's folder goes with `go.work`. */
export const FOLDER_OF: Readonly<Record<string, string>> = {
  python: "python/",
  typescript: "typescript/",
  java: "jvm/",
  kotlin: "jvm/",
  go: "go/ and go.work",
  rust: "rust/",
};

const REMOVAL = "/api/v1/languages/removal";

/** `a`, `a and b`, `a, b and c`. */
export function listed(items: readonly string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

export function removalTitle(languages: readonly string[]): string {
  return `Remove ${listed(languages)} from this workspace`;
}

/** The command a removal runs: the keep form, or `--delete-folder` once the learner chose that. */
export function removalCommand(languages: readonly string[], deleteFolders: boolean): string {
  return `cstudy lang remove ${languages.join(" ")}${deleteFolders ? " --delete-folder" : ""}`;
}

/** The request that previews a deletion of these languages' folders. */
export function removalUrl(languages: readonly string[]): string {
  return `${REMOVAL}?${new URLSearchParams(languages.map((language) => ["language", language])).toString()}`;
}

/** The folder of each language, once for a folder two languages share. */
export function foldersOf(languages: readonly string[]): readonly string[] {
  return [...new Set(languages.map((language) => FOLDER_OF[language] ?? `${language}/`))];
}

export function practiceFiles(count: number): string {
  return count === 1 ? "1 practice file" : `${count} practice files`;
}

/** `rust/ · 12 practice files`, one per folder that goes. */
export function deleteLines(preview: RemovalPreview): readonly string[] {
  return preview.delete.map(({ path, files }) => `${path} · ${practiceFiles(files)}`);
}

/** `jvm/: kotlin still uses it`, one per shared folder that stays. */
export function keepLines(preview: RemovalPreview): readonly string[] {
  return preview.keep.map(({ path, reason }) => `${path}: ${reason}`);
}

/** What always stays: `progress, .archive/, projects/ and notes/`. */
export function staysLine(preview: RemovalPreview): string {
  return `Always stays: ${listed(preview.stays)}.`;
}

/** The folders that go as the CLI's question lists them: Go's entry is `go/` and `go.work`. */
export function deletedFolders(preview: RemovalPreview): readonly string[] {
  return preview.delete.flatMap(({ path }) => path.split(" and "));
}

/** The button that deletes: `Delete rust/`, `Delete go/, go.work and rust/`; with no folder to
 * delete, only the removal is left to do. */
export function deleteAction(preview: RemovalPreview, languages: readonly string[]): string {
  const folders = deletedFolders(preview);
  return folders.length === 0 ? `Remove ${listed(languages)}` : `Delete ${listed(folders)}`;
}

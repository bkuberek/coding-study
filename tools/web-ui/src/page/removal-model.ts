/**
 * What the Settings view says of the languages a Save takes out of the workspace
 * (docs/specs/web-ui.md#settings-view), in the words of `cstudy lang remove`.
 */

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

export function practiceFiles(count: number): string {
  return count === 1 ? "1 practice file" : `${count} practice files`;
}

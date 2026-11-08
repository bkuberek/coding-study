/**
 * How the page names files to a language server (docs/specs/web-ui.md#code-intelligence-in-the-editor):
 * a `file://` URI built from the session's workspace, the tree's root and the file's path, and the
 * LSP language id of the file.
 */

import { type LanguageName, languageForPath } from "../languages.ts";

/** The catalog's language (`GET /api/v1/code-intelligence/languages`) whose server serves each
 * language of the editor; JavaScript and the JSX dialects go to the TypeScript server. */
const SERVER_LANGUAGES: Readonly<Partial<Record<LanguageName, string>>> = {
  python: "python",
  typescript: "typescript",
  tsx: "typescript",
  javascript: "typescript",
  jsx: "typescript",
  java: "java",
  kotlin: "kotlin",
  go: "go",
  rust: "rust",
};

const LANGUAGE_IDS: Readonly<Record<string, string>> = {
  py: "python",
  pyi: "python",
  ts: "typescript",
  mts: "typescript",
  cts: "typescript",
  tsx: "typescriptreact",
  js: "javascript",
  mjs: "javascript",
  cjs: "javascript",
  jsx: "javascriptreact",
  java: "java",
  kt: "kotlin",
  go: "go",
  rs: "rust",
};

const DRIVE_LETTER = /^[A-Za-z]:/;

/** The catalog language whose server serves the file, or null when none could. */
export function serverLanguageFor(path: string): string | null {
  const language = languageForPath(path);
  return language === null ? null : (SERVER_LANGUAGES[language] ?? null);
}

/** The LSP language id of a file the Python, TypeScript, Java, Kotlin, Go or Rust server opens, else null. */
export function languageIdFor(path: string): string | null {
  const name = path.slice(path.lastIndexOf("/") + 1);
  return LANGUAGE_IDS[name.slice(name.lastIndexOf(".") + 1).toLowerCase()] ?? null;
}

/** `file://` and the segments of the workspace, the root and the path, each as `encodeURIComponent`
 * writes it (a drive letter keeps its colon). */
export function fileUri(workspace: string, root: string, path: string): string {
  return fileUriOf(workspace, root, path);
}

export function rootUri(workspace: string, root: string): string {
  return fileUriOf(workspace, root);
}

function fileUriOf(...parts: string[]): string {
  const slashed = parts.map((part) => part.replaceAll("\\", "/")).filter((part) => part !== "");
  const segments = slashed.flatMap((part, index) => (index === 0 ? part : part.replace(/^\/+/, "")).split("/"));
  const drive = DRIVE_LETTER.test(segments[0] ?? "");
  const encoded = segments.map((segment, index) => (drive && index === 0 ? segment : encodeURIComponent(segment)));
  return `file://${drive ? "/" : ""}${encoded.join("/")}`;
}

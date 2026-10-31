/** The languages the editor highlights. TSX and JSX are the JSX dialects of TypeScript and JavaScript. */
export type LanguageName =
  | "python"
  | "typescript"
  | "tsx"
  | "javascript"
  | "jsx"
  | "java"
  | "kotlin"
  | "go"
  | "rust"
  | "json"
  | "toml"
  | "yaml"
  | "markdown";

const BY_EXTENSION: ReadonlyMap<string, LanguageName> = new Map([
  ["py", "python"],
  ["pyi", "python"],
  ["ts", "typescript"],
  ["mts", "typescript"],
  ["cts", "typescript"],
  ["tsx", "tsx"],
  ["js", "javascript"],
  ["mjs", "javascript"],
  ["cjs", "javascript"],
  ["jsx", "jsx"],
  ["java", "java"],
  ["kt", "kotlin"],
  ["kts", "kotlin"],
  ["go", "go"],
  ["rs", "rust"],
  ["json", "json"],
  ["toml", "toml"],
  ["yaml", "yaml"],
  ["yml", "yaml"],
  ["md", "markdown"],
  ["markdown", "markdown"],
]);

/** The language of a file by the extension of its name, or null when the editor has none for it. */
export function languageForPath(path: string): LanguageName | null {
  const name = path.slice(path.lastIndexOf("/") + 1);
  const dot = name.lastIndexOf(".");
  // A leading dot starts a hidden file's name, not an extension.
  if (dot <= 0) return null;
  return BY_EXTENSION.get(name.slice(dot + 1).toLowerCase()) ?? null;
}

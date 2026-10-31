import type { Extension } from "@codemirror/state";

import type { LanguageName } from "./languages.ts";

// Each grammar is a chunk of its own, fetched the first time a file needs it.
const LOADERS: Readonly<Record<LanguageName, () => Promise<Extension>>> = {
  python: async () => (await import("./grammars/python.ts")).languageSupport(),
  typescript: async () =>
    (await import("./grammars/javascript.ts")).languageSupport({ typescript: true }),
  tsx: async () =>
    (await import("./grammars/javascript.ts")).languageSupport({ typescript: true, jsx: true }),
  javascript: async () => (await import("./grammars/javascript.ts")).languageSupport(),
  jsx: async () => (await import("./grammars/javascript.ts")).languageSupport({ jsx: true }),
  java: async () => (await import("./grammars/java.ts")).languageSupport(),
  kotlin: async () => (await import("./grammars/kotlin.ts")).languageSupport(),
  go: async () => (await import("./grammars/go.ts")).languageSupport(),
  rust: async () => (await import("./grammars/rust.ts")).languageSupport(),
  json: async () => (await import("./grammars/json.ts")).languageSupport(),
  toml: async () => (await import("./grammars/toml.ts")).languageSupport(),
  yaml: async () => (await import("./grammars/yaml.ts")).languageSupport(),
  markdown: async () => (await import("./grammars/markdown.ts")).languageSupport(),
};

/** The highlighting and language support of a language, once its chunk has loaded. */
export function loadLanguage(name: LanguageName): Promise<Extension> {
  return LOADERS[name]();
}

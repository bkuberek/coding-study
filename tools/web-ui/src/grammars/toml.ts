import { StreamLanguage } from "@codemirror/language";
import { toml } from "@codemirror/legacy-modes/mode/toml";

// CodeMirror has no Lezer grammar for TOML; the legacy mode tokenizes it.
export const languageSupport = () => StreamLanguage.define(toml);

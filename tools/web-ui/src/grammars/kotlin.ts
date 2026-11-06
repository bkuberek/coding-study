import { indentUnit, StreamLanguage } from "@codemirror/language";
import { kotlin } from "@codemirror/legacy-modes/mode/clike";

// CodeMirror has no Lezer grammar for Kotlin; the legacy mode tokenizes it.
export const languageSupport = () => [StreamLanguage.define(kotlin), indentUnit.of("    ")];

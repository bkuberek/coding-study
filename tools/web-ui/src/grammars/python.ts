import { python } from "@codemirror/lang-python";
import { indentUnit } from "@codemirror/language";

export const languageSupport = () => [python(), indentUnit.of("    ")];

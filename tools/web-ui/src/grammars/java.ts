import { java } from "@codemirror/lang-java";
import { indentUnit } from "@codemirror/language";

export const languageSupport = () => [java(), indentUnit.of("    ")];

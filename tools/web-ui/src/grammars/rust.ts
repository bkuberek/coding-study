import { rust } from "@codemirror/lang-rust";
import { indentUnit } from "@codemirror/language";

export const languageSupport = () => [rust(), indentUnit.of("    ")];

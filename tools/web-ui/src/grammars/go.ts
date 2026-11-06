import { go } from "@codemirror/lang-go";
import { indentUnit } from "@codemirror/language";
import { EditorState } from "@codemirror/state";

// gofmt's own: a tab, which shows four columns wide.
export const languageSupport = () => [go(), indentUnit.of("\t"), EditorState.tabSize.of(4)];

import { markdownKeymap, markdownLanguage } from "@codemirror/lang-markdown";
import { LanguageSupport } from "@codemirror/language";
import { Prec } from "@codemirror/state";
import { keymap } from "@codemirror/view";

// GitHub-flavoured Markdown and its list keys, without `markdown()`'s highlighting of embedded HTML,
// which brings the HTML, CSS and JavaScript grammars and doubles the chunk.
export const languageSupport = () => new LanguageSupport(markdownLanguage, Prec.high(keymap.of(markdownKeymap)));

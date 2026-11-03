import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import type { Extension } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { tags } from "@lezer/highlight";

export type ThemeName = "light" | "dark";

/**
 * One theme's colours. Both themes share their hue families (rust keywords, green strings, plum
 * literals, blue functions, ochre types), so a file reads the same in either; every pair of text
 * and background meets WCAG AA (4.5:1).
 */
interface Palette {
  readonly background: string;
  readonly foreground: string;
  readonly gutter: string;
  readonly border: string;
  readonly panel: string;
  readonly activeLine: string;
  readonly selection: string;
  readonly searchMatch: string;
  readonly accent: string;
  readonly comment: string;
  readonly keyword: string;
  readonly string: string;
  readonly literal: string;
  readonly function: string;
  readonly type: string;
  readonly property: string;
  readonly operator: string;
  readonly meta: string;
  readonly invalid: string;
}

const LIGHT: Palette = {
  background: "#fbf8f2",
  foreground: "#24272d",
  gutter: "#686c74",
  border: "#e2dacb",
  panel: "#f3eee3",
  activeLine: "#f3ede1",
  selection: "#d6e2ee",
  searchMatch: "#f5dd9c",
  accent: "#a63f18",
  comment: "#5f636b",
  keyword: "#9a3b10",
  string: "#2c6a3d",
  literal: "#7a3d9e",
  function: "#1d5b89",
  type: "#855300",
  property: "#3a4a5b",
  operator: "#4e545d",
  meta: "#76592b",
  invalid: "#b3261e",
};

const DARK: Palette = {
  background: "#16191e",
  foreground: "#dde1e6",
  gutter: "#8f96a0",
  border: "#2a2f37",
  panel: "#1c2026",
  activeLine: "#1e2228",
  selection: "#25334a",
  searchMatch: "#5b4a1d",
  accent: "#f0915a",
  comment: "#9aa2ad",
  keyword: "#f0915a",
  string: "#a5d38f",
  literal: "#d3a3ec",
  function: "#86c1f0",
  type: "#e8c36a",
  property: "#c8d0da",
  operator: "#aeb6c1",
  meta: "#c9a36b",
  invalid: "#ff8f87",
};

const MONOSPACE =
  'ui-monospace, "SF Mono", "JetBrains Mono", "Cascadia Code", Menlo, Consolas, "Liberation Mono", monospace';

/** The editor's chrome. The page may set `--cs-editor-background`, `--cs-editor-foreground`,
 * `--cs-editor-font` and `--cs-editor-font-size` to match its own. */
function chrome(palette: Palette, dark: boolean): Extension {
  const background = `var(--cs-editor-background, ${palette.background})`;
  const foreground = `var(--cs-editor-foreground, ${palette.foreground})`;
  return EditorView.theme(
    {
      "&": { color: foreground, backgroundColor: background, fontSize: "var(--cs-editor-font-size, 14px)" },
      "&.cm-focused": { outline: `2px solid ${palette.accent}`, outlineOffset: "-2px" },
      ".cm-scroller": { fontFamily: `var(--cs-editor-font, ${MONOSPACE})`, lineHeight: "1.55" },
      ".cm-content": { caretColor: palette.accent },
      ".cm-cursor, .cm-dropCursor": { borderLeft: `2px solid ${palette.accent}` },
      "&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection":
        { backgroundColor: palette.selection },
      ".cm-activeLine": { backgroundColor: palette.activeLine },
      ".cm-gutters": { backgroundColor: background, color: palette.gutter, borderRight: `1px solid ${palette.border}` },
      ".cm-activeLineGutter": { backgroundColor: palette.activeLine, color: foreground },
      ".cm-foldPlaceholder": { backgroundColor: "transparent", border: "none", color: palette.gutter },
      "&.cm-focused .cm-matchingBracket": { backgroundColor: palette.selection, outline: `1px solid ${palette.gutter}` },
      "&.cm-focused .cm-nonmatchingBracket": { outline: `1px solid ${palette.invalid}` },
      ".cm-searchMatch": { backgroundColor: palette.searchMatch },
      ".cm-searchMatch.cm-searchMatch-selected": { outline: `1px solid ${palette.accent}` },
      ".cm-panels": { backgroundColor: palette.panel, color: foreground },
      ".cm-panels.cm-panels-top": { borderBottom: `1px solid ${palette.border}` },
      ".cm-panels.cm-panels-bottom": { borderTop: `1px solid ${palette.border}` },
      ".cm-tooltip": { backgroundColor: palette.panel, color: foreground, border: `1px solid ${palette.border}` },
      ".cm-tooltip-autocomplete > ul > li[aria-selected]": { backgroundColor: palette.selection, color: foreground },
    },
    { dark },
  );
}

function highlighting(palette: Palette, dark: boolean): Extension {
  const style = HighlightStyle.define(
    [
      { tag: [tags.comment, tags.docComment], color: palette.comment, fontStyle: "italic" },
      { tag: [tags.keyword, tags.controlKeyword, tags.definitionKeyword, tags.moduleKeyword], color: palette.keyword },
      { tag: [tags.string, tags.special(tags.string), tags.regexp, tags.character], color: palette.string },
      { tag: [tags.number, tags.bool, tags.null, tags.atom, tags.constant(tags.name)], color: palette.literal },
      { tag: [tags.function(tags.variableName), tags.function(tags.propertyName), tags.definition(tags.function(tags.variableName))], color: palette.function },
      { tag: [tags.typeName, tags.className, tags.namespace, tags.standard(tags.typeName)], color: palette.type },
      { tag: [tags.propertyName, tags.attributeName, tags.labelName], color: palette.property },
      { tag: [tags.operator, tags.punctuation, tags.bracket, tags.separator], color: palette.operator },
      { tag: [tags.meta, tags.annotation, tags.processingInstruction], color: palette.meta },
      { tag: tags.invalid, color: palette.invalid },
      { tag: tags.heading, color: palette.keyword, fontWeight: "bold" },
      { tag: tags.strong, fontWeight: "bold" },
      { tag: tags.emphasis, fontStyle: "italic" },
      { tag: tags.strikethrough, textDecoration: "line-through" },
      { tag: [tags.link, tags.url], color: palette.function, textDecoration: "underline" },
      { tag: tags.monospace, color: palette.string },
    ],
    { themeType: dark ? "dark" : "light" },
  );
  return syntaxHighlighting(style);
}

/** The chrome and syntax colours of a theme. */
export function themeExtension(name: ThemeName): Extension {
  const dark = name === "dark";
  const palette = dark ? DARK : LIGHT;
  return [chrome(palette, dark), highlighting(palette, dark)];
}

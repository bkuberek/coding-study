/**
 * What a hover answer holds (docs/specs/web-ui.md#documentation and #hover): HTML only from a
 * `cstudy-html` value, which the broker rendered and made safe; every other string a server sent
 * is text. And the sentence a screen reader hears when a hover opens from the keyboard.
 */

/** Content of a hover tooltip: HTML the broker rendered, or text to show as text. */
export type HoverContent = { readonly kind: "html"; readonly html: string } | { readonly kind: "text"; readonly text: string };

const HTML_KIND = "cstudy-html";
const ENTITIES: Readonly<Record<string, string>> = { "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&amp;": "&" };
const PARAGRAPH = /<p(?:\s[^>]*)?>([\s\S]*?)<\/p>/;
const PLAIN_TEXT = /<pre class="doc-plain">([\s\S]*?)<\/pre>/;
const PREFORMATTED = /<pre(?:\s[^>]*)?>([\s\S]*?)<\/pre>/;
const BLANK_LINE = /\n\s*\n/;

/** The content of the `contents` of a hover answer, or null when there is nothing to show. */
export function hoverContent(contents: unknown): HoverContent | null {
  if (typeof contents === "object" && contents !== null && "kind" in contents && contents.kind === HTML_KIND) {
    const html = "value" in contents && typeof contents.value === "string" ? contents.value : "";
    return html.trim() === "" ? null : { kind: "html", html };
  }
  const text = textOf(contents);
  return text.trim() === "" ? null : { kind: "text", text };
}

function textOf(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(textOf).filter((part) => part.trim() !== "").join("\n\n");
  if (typeof value === "object" && value !== null && "value" in value && typeof value.value === "string") return value.value;
  return "";
}

/** The first paragraph of rendered documentation as plain text, else the first code block's text. */
export function firstParagraph(html: string): string {
  const paragraph = PARAGRAPH.exec(html);
  if (paragraph !== null) return plain(paragraph[1] ?? "");
  const text = PLAIN_TEXT.exec(html);
  if (text !== null) return plain((text[1] ?? "").split(BLANK_LINE)[0] ?? "");
  const code = PREFORMATTED.exec(html);
  return code === null ? "" : plain(code[1] ?? "");
}

function plain(fragment: string): string {
  const text = fragment.replace(/<[^>]*>/g, "").replace(/&(?:lt|gt|quot|#39|amp);/g, (entity) => ENTITIES[entity] ?? entity);
  return text.replace(/\s+/g, " ").trim();
}

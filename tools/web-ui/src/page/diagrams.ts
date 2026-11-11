/**
 * Draws a guide's Mermaid diagrams as SVG (docs/specs/web-ui.md#guides-view). This module and
 * Mermaid are chunks of their own, which the Guides view fetches only when it opens a guide that
 * has a diagram; they come from this server, like every other file of the page.
 *
 * The page's Content Security Policy lets in a style element only with the page's nonce, and no
 * `style` attribute at all, even in a document a parser makes aside, as DOMPurify's. Mermaid adds
 * a style element to each diagram and sets `style` attributes as it lays one out, then sanitizes
 * the SVG with DOMPurify, which parses it again. So while it draws, each style element it creates
 * gets the nonce, each `style` attribute is set through the CSSOM instead, which the policy
 * allows, and markup about to be parsed carries each `style` attribute as `data-cs-style` and the
 * nonce on each style element. The SVG it returns is parsed in a template and comes into the page
 * with its styles set through the CSSOM and its style elements made again with the nonce. Each
 * diagram keeps the `<title>` and `<desc>` Mermaid makes of its `accTitle` and `accDescr`, which
 * name and describe it to a screen reader.
 */

import mermaid from "mermaid";

import { type DiagramTheme, mermaidOptions } from "./guides-model.ts";

const STYLE = "style";
const KEPT_STYLE = "data-cs-style";
const STYLE_ATTRIBUTE = / style="([^"]*)"/g;
const STYLE_ELEMENT = /<style(?=[\s>])/g;
let drawings = 0;
/** Mermaid's configuration is global, so one diagram is drawn at a time. */
let queue: Promise<unknown> = Promise.resolve();

/** Draws each figure's `data-mermaid` in `theme`, replacing a drawing in another theme. A diagram
 * Mermaid cannot draw shows its text drawing instead. */
export function drawDiagrams(figures: readonly HTMLElement[], theme: DiagramTheme, nonce: string): Promise<void> {
  const drawn = queue.then(async () => {
    mermaid.initialize(mermaidOptions(theme));
    for (const figure of figures) await drawOne(figure, theme, nonce);
  });
  queue = drawn.catch(() => undefined);
  return drawn;
}

async function drawOne(figure: HTMLElement, theme: DiagramTheme, nonce: string): Promise<void> {
  if (!figure.isConnected || figure.dataset["drawn"] === theme) return;
  drawings += 1;
  try {
    const { svg } = await withAllowedStyles(nonce, () => mermaid.render(`diagram-${drawings}`, figure.dataset["mermaid"] ?? ""));
    if (!figure.isConnected) return;
    figure.querySelector(":scope > svg")?.remove();
    insertDrawing(figure, svg, nonce);
    figure.dataset["drawn"] = theme;
    figure.removeAttribute("aria-busy");
  } catch {
    showText(figure);
  }
}

/** The text drawing that guide.md holds for every diagram, as the terminal shows it. */
function showText(figure: HTMLElement): void {
  figure.removeAttribute("aria-busy");
  figure.dataset["drawn"] = "text";
  const text = figure.querySelector<HTMLElement>(".diagram-text");
  if (text !== null) text.hidden = false;
}

/** Markup whose `style` attributes are `data-cs-style` ones and whose style elements carry the
 * nonce, so a parser applies no style the policy refuses. Serialized markup quotes every attribute
 * value with `"`, which it writes as `&quot;` inside one. */
function allowedMarkup(markup: string, nonce: string): string {
  return markup.replace(STYLE_ATTRIBUTE, ` ${KEPT_STYLE}="$1"`).replace(STYLE_ELEMENT, `<style nonce="${nonce}"`);
}

/** Runs `draw` with each style element created given the nonce, each `style` attribute set
 * through the CSSOM, and each document parsed from markup parsed from `allowedMarkup`. */
async function withAllowedStyles<Result>(nonce: string, draw: () => Promise<Result>): Promise<Result> {
  const createElement = Document.prototype.createElement;
  const setAttribute = Element.prototype.setAttribute;
  const parseFromString = DOMParser.prototype.parseFromString;
  // DOMPurify hands over a TrustedHTML where the browser has Trusted Types; its text is the markup.
  DOMParser.prototype.parseFromString = function (this: DOMParser, markup: string, type: DOMParserSupportedType): Document {
    return parseFromString.call(this, allowedMarkup(String(markup), nonce), type);
  } as typeof parseFromString;
  Document.prototype.createElement = function (this: Document, tag: string, options?: ElementCreationOptions): HTMLElement {
    const element = createElement.call(this, tag, options);
    if (element instanceof HTMLStyleElement) element.nonce = nonce;
    return element;
  } as typeof createElement;
  Element.prototype.setAttribute = function (this: Element, name: string, value: string): void {
    if (name.toLowerCase() === STYLE && (this instanceof HTMLElement || this instanceof SVGElement)) {
      this.style.cssText = value;
      return;
    }
    setAttribute.call(this, name, value);
  };
  try {
    return await draw();
  } finally {
    Document.prototype.createElement = createElement;
    Element.prototype.setAttribute = setAttribute;
    DOMParser.prototype.parseFromString = parseFromString;
  }
}

/** Puts the SVG first in the figure: its style elements are made again with the nonce, and its
 * `style` attributes are set through the CSSOM once it is in the page. */
function insertDrawing(figure: HTMLElement, svg: string, nonce: string): void {
  const template = document.createElement("template");
  template.innerHTML = allowedMarkup(svg, nonce);
  const drawing = template.content.querySelector("svg");
  if (drawing === null) throw new Error("Mermaid drew no SVG");
  const styled = [drawing, ...drawing.querySelectorAll<SVGElement>(`[${KEPT_STYLE}]`)].flatMap((element) => {
    const css = element.getAttribute(KEPT_STYLE);
    element.removeAttribute(KEPT_STYLE);
    return css === null ? [] : [[element, css] as const];
  });
  const sheets = [...drawing.querySelectorAll(STYLE)].map((sheet) => {
    sheet.remove();
    return sheet.textContent ?? "";
  });
  figure.prepend(drawing);
  for (const [element, css] of styled) element.style.cssText = css;
  for (const css of sheets.reverse()) {
    const sheet = document.createElement(STYLE);
    sheet.nonce = nonce;
    sheet.textContent = css;
    drawing.prepend(sheet);
  }
}

/**
 * Building elements without HTML strings: text is always a text node, so nothing a file or a
 * problem holds can become markup. No element gets a `style` attribute, which the page's Content
 * Security Policy refuses; the stylesheet and classes do the styling.
 */

export type Child = Node | string | number | null | undefined | false;
type Value = string | number | boolean | null | undefined;
export type Attributes = Readonly<Record<string, Value | EventListener>>;

export function h<Tag extends keyof HTMLElementTagNameMap>(
  tag: Tag,
  attributes: Attributes = {},
  ...children: Child[]
): HTMLElementTagNameMap[Tag] {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (typeof value === "function") {
      element.addEventListener(name.slice(2).toLowerCase(), value);
    } else if (value === true) {
      element.setAttribute(name, "");
    } else if (value !== false && value !== null && value !== undefined) {
      element.setAttribute(name, String(value));
    }
  }
  element.append(...nodes(children));
  return element;
}

export function nodes(children: readonly Child[]): (Node | string)[] {
  return children.flatMap((child) =>
    child === null || child === undefined || child === false ? [] : [typeof child === "number" ? String(child) : child],
  );
}

/** A `<code>` that a screen reader reads as a command. */
export function command(text: string): HTMLElement {
  return h("code", { class: "cmd" }, text);
}

/** A glyph and its word, so a status never depends on colour alone. */
export function badge(glyph: string, text: string, tone: string): HTMLElement {
  return h(
    "span",
    { class: `badge tone-${tone}` },
    glyph ? h("span", { class: "glyph", "aria-hidden": "true" }, glyph) : null,
    text,
  );
}

/** Server-rendered Markdown (docs/specs/web-ui.md#security): raw HTML is escaped on the server.
 * Each code block takes the focus, so the keyboard scrolls the lines too wide for it. */
export function rendered(html: string, className: string): HTMLElement {
  const container = h("div", { class: className });
  container.innerHTML = html;
  for (const link of container.querySelectorAll<HTMLAnchorElement>("a[href^='http']")) {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  }
  for (const block of container.querySelectorAll("pre")) block.tabIndex = 0;
  return container;
}

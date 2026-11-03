/**
 * Stands in for `marked` in the code-intelligence chunk (`scripts/build.ts` aliases the package to
 * this module): the server renders all documentation as `cstudy-html` (docs/specs/web-ui.md#documentation),
 * so `@codemirror/lsp-client`'s own Markdown renderer is never wanted. It exports what the package
 * imports and returns its input with the HTML characters escaped, so even a path that did reach
 * it would insert text, never markup.
 */

const ESCAPES: Readonly<Record<string, string>> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export class Marked {
  // The package passes `walkTokens`; there are no tokens to walk.
  constructor(_options?: unknown) {}

  parse(text: string, _options?: unknown): string {
    return text.replace(/[&<>"']/g, (character) => ESCAPES[character] ?? character);
  }
}

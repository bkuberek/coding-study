const HTML_ENTITIES = new Map<string, string>([
  ["&", "&amp;"],
  ["<", "&lt;"],
  [">", "&gt;"],
  ['"', "&quot;"],
  ["'", "&#x27;"],
]);
const ASCII_ALPHANUMERIC = /^[A-Za-z0-9]$/;
const URL_UNRESERVED = /^[A-Za-z0-9\-._~]$/;

function encodeHtml(text: string): string {
  let encoded = "";
  for (const character of text) {
    encoded += HTML_ENTITIES.get(character) ?? character;
  }
  return encoded;
}

function encodeUrlQuery(text: string): string {
  // encodeURIComponent leaves ! ' ( ) * as they are, so the bytes are encoded here instead.
  let encoded = "";
  for (const byte of new TextEncoder().encode(text)) {
    const character = String.fromCharCode(byte);
    encoded += URL_UNRESERVED.test(character)
      ? character
      : "%" + byte.toString(16).toUpperCase().padStart(2, "0");
  }
  return encoded;
}

function encodeJsString(text: string): string {
  // Indexing a string walks UTF-16 code units, which is what a \u escape names.
  let encoded = "";
  for (let index = 0; index < text.length; index++) {
    const character = text[index];
    encoded += ASCII_ALPHANUMERIC.test(character)
      ? character
      : "\\u" + text.charCodeAt(index).toString(16).toUpperCase().padStart(4, "0");
  }
  return encoded;
}

const ENCODERS = new Map<string, (text: string) => string>([
  ["html-text", encodeHtml],
  ["html-attribute", encodeHtml],
  ["url-query", encodeUrlQuery],
  ["js-string", encodeJsString],
]);

export function encodeOutput(text: string, context: string): string {
  const encoder = ENCODERS.get(context);
  return encoder === undefined ? "" : encoder(text);
}

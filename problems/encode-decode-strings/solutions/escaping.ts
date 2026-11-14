const ESCAPE = "\\";
const TERMINATOR = ",";

function escape(text: string): string {
  // Escape the escape character first, or the escapes added for terminators get doubled.
  return text.replaceAll(ESCAPE, ESCAPE + ESCAPE).replaceAll(TERMINATOR, ESCAPE + TERMINATOR);
}

function encode(strs: string[]): string {
  return strs.map((text) => escape(text) + TERMINATOR).join("");
}

function decode(encoded: string): string[] {
  const strs: string[] = [];
  let current = "";
  let escaped = false;
  for (const character of encoded) {
    if (escaped) {
      current += character;
      escaped = false;
    } else if (character === ESCAPE) {
      escaped = true;
    } else if (character === TERMINATOR) {
      strs.push(current);
      current = "";
    } else {
      current += character;
    }
  }
  return strs;
}

export function encodeDecode(strs: string[]): string[] {
  return decode(encode(strs));
}

const MARKER = "#";

function encode(strs: string[]): string {
  return strs.map((text) => `${text.length}${MARKER}${text}`).join("");
}

function decode(encoded: string): string[] {
  const strs: string[] = [];
  let position = 0;
  while (position < encoded.length) {
    // A length has only digits, so the first marker after it ends the length.
    const marker = encoded.indexOf(MARKER, position);
    const start = marker + 1;
    const end = start + Number(encoded.slice(position, marker));
    strs.push(encoded.slice(start, end));
    position = end;
  }
  return strs;
}

export function encodeDecode(strs: string[]): string[] {
  return decode(encode(strs));
}

const DELIMITERS = ["<memory>", "</memory>"];
const DELIMITER_END = ">";
const ROLE_MARKER = /^[ \t]*(system|assistant|developer|tool):/i;
const DELIMITERS_REMOVED = "delimiters removed";
const TRUNCATED = "truncated";

// The text with no delimiter left in it, even one that a removal joined together. Each
// character goes onto a stack, and a delimiter is popped the moment its last character arrives.
// What sits below the top never changes, so the stack never holds a delimiter.
function removeDelimiters(text: string): [string, boolean] {
  const kept: string[] = [];
  let removed = false;
  for (const character of text) {
    kept.push(character);
    if (character !== DELIMITER_END) {
      continue;
    }
    const delimiter = DELIMITERS.find((d) => kept.slice(-d.length).join("").toLowerCase() === d);
    if (delimiter !== undefined) {
      kept.length -= delimiter.length;
      removed = true;
    }
  }
  return [kept.join(""), removed];
}

function roleMarkerFlags(text: string): string[] {
  const flags: string[] = [];
  text.split("\n").forEach((line, index) => {
    const marker = ROLE_MARKER.exec(line);
    if (marker !== null) {
      flags.push(`line ${index + 1}: ${marker[1].toLowerCase()}`);
    }
  });
  return flags;
}

export function sanitizeMemory(text: string, maxLength: number): string[] {
  const [withoutDelimiters, removed] = removeDelimiters(text);
  const flags = removed ? [DELIMITERS_REMOVED] : [];
  const tooLong = withoutDelimiters.length > maxLength;
  if (tooLong) {
    flags.push(TRUNCATED);
  }
  const cleaned = tooLong ? withoutDelimiters.slice(0, maxLength) : withoutDelimiters;
  flags.push(...roleMarkerFlags(cleaned));
  return [cleaned, ...flags];
}

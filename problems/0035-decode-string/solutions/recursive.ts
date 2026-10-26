function isDigit(character: string): boolean {
  return character >= "0" && character <= "9";
}

export function decodeString(s: string): string {
  let position = 0;

  // Decode up to the "]" that closes the current group, or to the end of the string.
  function decodeGroup(): string {
    const parts: string[] = [];
    let count = 0;
    while (position < s.length) {
      const character = s[position++];
      if (isDigit(character)) {
        count = count * 10 + Number(character);
      } else if (character === "[") {
        parts.push(decodeGroup().repeat(count));
        count = 0;
      } else if (character === "]") {
        break;
      } else {
        parts.push(character);
      }
    }
    return parts.join("");
  }

  return decodeGroup();
}

export function decodeString(s: string): string {
  // For every open group: its repeat count and the text built before its "[".
  const counts: number[] = [];
  const outerTexts: string[] = [];
  let current = "";
  let count = 0;
  for (const character of s) {
    if (character >= "0" && character <= "9") {
      count = count * 10 + Number(character);
    } else if (character === "[") {
      counts.push(count);
      outerTexts.push(current);
      current = "";
      count = 0;
    } else if (character === "]") {
      current = (outerTexts.pop() as string) + current.repeat(counts.pop() as number);
    } else {
      current += character;
    }
  }
  return current;
}

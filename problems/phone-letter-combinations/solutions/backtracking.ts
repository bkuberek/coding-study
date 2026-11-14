const KEYPAD: Readonly<Record<string, string>> = {
  "2": "abc",
  "3": "def",
  "4": "ghi",
  "5": "jkl",
  "6": "mno",
  "7": "pqrs",
  "8": "tuv",
  "9": "wxyz",
};

export function letterCombinations(digits: string): string[] {
  if (digits.length === 0) {
    return [];
  }
  const words: string[] = [];
  const letters = new Array<string>(digits.length).fill("");
  const fill = (slot: number): void => {
    if (slot === digits.length) {
      words.push(letters.join(""));
      return;
    }
    for (const letter of KEYPAD[digits[slot]]) {
      letters[slot] = letter;
      fill(slot + 1);
    }
  };
  fill(0);
  return words;
}

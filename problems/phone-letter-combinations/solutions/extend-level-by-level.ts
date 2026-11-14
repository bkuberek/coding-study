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
  let words = [""];
  for (const digit of digits) {
    words = words.flatMap((word) => [...KEYPAD[digit]].map((letter) => word + letter));
  }
  return words;
}

const LETTERS = 26;
const A = "a".charCodeAt(0);

export function alienOrder(words: string[]): string {
  const present = new Array<boolean>(LETTERS).fill(false);
  for (const word of words) {
    for (let k = 0; k < word.length; k++) {
      present[word.charCodeAt(k) - A] = true;
    }
  }
  // before[x][y]: letter x must come before letter y. A matrix dedupes repeated rules.
  const before = Array.from({ length: LETTERS }, () => new Array<boolean>(LETTERS).fill(false));
  for (let i = 0; i + 1 < words.length; i++) {
    const first = words[i];
    const second = words[i + 1];
    const shorter = Math.min(first.length, second.length);
    let k = 0;
    while (k < shorter && first[k] === second[k]) {
      k++;
    }
    if (k < shorter) {
      before[first.charCodeAt(k) - A][second.charCodeAt(k) - A] = true;
    } else if (first.length > second.length) {
      return ""; // a word placed before its own proper prefix
    }
  }
  const waiting = new Array<number>(LETTERS).fill(0);
  for (let x = 0; x < LETTERS; x++) {
    for (let y = 0; y < LETTERS; y++) {
      if (before[x][y]) {
        waiting[y]++;
      }
    }
  }
  const order: number[] = [];
  for (let x = 0; x < LETTERS; x++) {
    if (present[x] && waiting[x] === 0) {
      order.push(x);
    }
  }
  for (let head = 0; head < order.length; head++) {
    const x = order[head];
    for (let y = 0; y < LETTERS; y++) {
      if (before[x][y] && --waiting[y] === 0) {
        order.push(y);
      }
    }
  }
  const letterCount = present.filter(Boolean).length;
  return order.length === letterCount ? String.fromCharCode(...order.map((x) => x + A)) : "";
}

const LETTERS = 26;
const A = "a".charCodeAt(0);
const UNVISITED = 0;
const ON_PATH = 1;
const DONE = 2;

export function alienOrder(words: string[]): string {
  const present = new Array<boolean>(LETTERS).fill(false);
  for (const word of words) {
    for (let k = 0; k < word.length; k++) {
      present[word.charCodeAt(k) - A] = true;
    }
  }
  // before[x][y]: letter x must come before letter y.
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
  const state = new Array<number>(LETTERS).fill(UNVISITED);
  const finished: number[] = []; // each letter lands here after every letter that must follow it
  // Emit everything after x, then x; false if a rule loops back.
  const visit = (x: number): boolean => {
    state[x] = ON_PATH;
    for (let y = 0; y < LETTERS; y++) {
      if (!before[x][y]) {
        continue;
      }
      if (state[y] === ON_PATH || (state[y] === UNVISITED && !visit(y))) {
        return false;
      }
    }
    state[x] = DONE;
    finished.push(x);
    return true;
  };
  for (let x = 0; x < LETTERS; x++) {
    if (present[x] && state[x] === UNVISITED && !visit(x)) {
      return "";
    }
  }
  return String.fromCharCode(...finished.reverse().map((x) => x + A));
}

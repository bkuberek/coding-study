export function replaceWords(dictionary: string[], sentence: string): string {
  const shortened = sentence.split(" ").map((word) => {
    let best = word;
    for (const root of dictionary) {
      if (root.length < best.length && word.startsWith(root)) {
        best = root;
      }
    }
    return best;
  });
  return shortened.join(" ");
}

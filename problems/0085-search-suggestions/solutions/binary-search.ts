export function suggestedProducts(products: string[], searchWord: string): string[][] {
  // The default sort compares UTF-16 code units, which is alphabetical for lowercase letters.
  const ordered = [...products].sort();
  const suggestions: string[][] = [];
  let start = 0;
  for (let typed = 1; typed <= searchWord.length; typed++) {
    const prefix = searchWord.slice(0, typed);
    start = lowerBound(ordered, prefix, start);
    suggestions.push(ordered.slice(start, start + 3).filter((product) => product.startsWith(prefix)));
  }
  return suggestions;
}

/** First index at or after `from` whose product is not smaller than `target`. */
function lowerBound(ordered: string[], target: string, from: number): number {
  let low = from;
  let high = ordered.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (ordered[middle] < target) low = middle + 1;
    else high = middle;
  }
  return low;
}

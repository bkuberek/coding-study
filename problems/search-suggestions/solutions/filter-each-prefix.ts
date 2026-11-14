export function suggestedProducts(products: string[], searchWord: string): string[][] {
  const suggestions: string[][] = [];
  for (let typed = 1; typed <= searchWord.length; typed++) {
    const prefix = searchWord.slice(0, typed);
    // The default sort compares UTF-16 code units, which is alphabetical for lowercase letters.
    const matches = products.filter((product) => product.startsWith(prefix)).sort();
    suggestions.push(matches.slice(0, 3));
  }
  return suggestions;
}

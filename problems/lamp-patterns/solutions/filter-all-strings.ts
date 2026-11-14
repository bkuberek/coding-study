export function lampPatterns(n: number): string[] {
  const result: string[] = [];
  for (let number = 0; number < 2 ** n; number++) {
    // Counting up writes the strings in increasing order; the bits are the lamps.
    const pattern = number.toString(2).padStart(n, "0");
    if (!pattern.includes("11")) {
      result.push(pattern);
    }
  }
  return result;
}

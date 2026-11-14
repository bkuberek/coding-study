function compareText(a: string, b: string): number {
  if (a < b) return -1;
  return a > b ? 1 : 0;
}

export function topRegions(regions: string[], totalsCents: number[], limit: number): string[] {
  const order = regions.map((_, index) => index);
  order.sort(
    (a, b) => totalsCents[b] - totalsCents[a] || compareText(regions[a], regions[b]),
  );
  return order.slice(0, limit).map((index) => `${regions[index]}: ${totalsCents[index]}`);
}

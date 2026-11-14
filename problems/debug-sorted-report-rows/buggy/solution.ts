// Debug: Sorted Report Rows. Some tests fail: find the bugs and fix them.

export function topRegions(regions: string[], totalsCents: number[], limit: number): string[] {
  const ranked = totalsCents.sort().reverse();
  const rows: string[] = [];
  for (const total of ranked.slice(0, limit)) {
    const region = regions[totalsCents.indexOf(total)];
    rows.push(`${region}: ${total}`);
  }
  return rows;
}

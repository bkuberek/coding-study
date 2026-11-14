import { Decimal } from "#support";

interface Change {
  code: string;
  percent: Decimal;
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export function rateChangeImpact(
  oldCodes: string[],
  oldRates: Decimal[],
  newCodes: string[],
  newRates: Decimal[],
): string[][] {
  const old = new Map<string, Decimal>();
  oldCodes.forEach((code, i) => old.set(code, oldRates[i]));
  const current = new Map<string, Decimal>();
  newCodes.forEach((code, i) => current.set(code, newRates[i]));

  const changed: Change[] = [];
  const added: string[] = [];
  for (const [code, rate] of current) {
    const before = old.get(code);
    if (before === undefined) {
      added.push(code);
    } else if (!rate.eq(before)) {
      // Rounded once to two places; a bigint has no negative zero, so a tiny decrease prints 0.00.
      changed.push({ code, percent: rate.minus(before).times(new Decimal(100)).div(before, 2, "HALF_UP") });
    }
  }
  const removed = [...old.keys()].filter((code) => !current.has(code));

  // Numeric order of the rounded percent, largest first; ties by code.
  changed.sort((a, b) => b.percent.cmp(a.percent) || compareText(a.code, b.code));
  added.sort(compareText);
  removed.sort(compareText);
  return [
    ...changed.map(({ code, percent }) => [code, "changed", percent.toString()]),
    ...added.map((code) => [code, "added", ""]),
    ...removed.map((code) => [code, "removed", ""]),
  ];
}

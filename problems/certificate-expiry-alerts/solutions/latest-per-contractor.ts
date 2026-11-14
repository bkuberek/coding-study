import type { IsoDate } from "#support";

const MILLIS_PER_DAY = 86_400_000;

function addDays(day: IsoDate, days: number): IsoDate {
  return new Date(Date.parse(day) + days * MILLIS_PER_DAY).toISOString().slice(0, 10);
}

export function certificateAlerts(
  contractorIds: string[],
  expiryDates: IsoDate[],
  asOfDate: IsoDate,
  windowDays: number,
): string[][] {
  const latest = new Map<string, IsoDate>(); // a renewal supersedes: only the latest expiry per contractor counts
  contractorIds.forEach((contractor, i) => {
    const known = latest.get(contractor);
    if (known === undefined || expiryDates[i] > known) {
      latest.set(contractor, expiryDates[i]);
    }
  });
  const horizon = addDays(asOfDate, windowDays);
  const flagged = [...latest].filter(([, expiry]) => expiry <= horizon);
  // ISO dates and ASCII ids compare correctly with <; localeCompare would not.
  flagged.sort(([idA, dateA], [idB, dateB]) => {
    if (dateA !== dateB) {
      return dateA < dateB ? -1 : 1;
    }
    return idA < idB ? -1 : idA > idB ? 1 : 0;
  });
  return flagged.map(([contractor, expiry]) => [
    contractor,
    expiry,
    expiry <= asOfDate ? "expired" : "expiring",
  ]);
}

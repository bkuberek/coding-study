// The one form a day takes in this API.

const DAY = /^(\d{4})-(\d{2})-(\d{2})$/;

/** Whether `text` is a day that exists, written YYYY-MM-DD. */
export function isRealDay(text: string): boolean {
  const parts = DAY.exec(text);
  if (parts === null) {
    return false;
  }
  const [year, month, day] = parts.slice(1).map(Number) as [number, number, number];
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

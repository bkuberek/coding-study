// Reading a form's text. Each reader takes the text as a person wrote it and answers the number it
// says, or null. They work on the digits: `parseFloat` would read "1,250.00" as 1.

const MONEY = /^\$?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?$/;
const RATE = /^(\d+)(?:\.(\d{1,2}))?%?$/;
const MONTHS = /^(\d+)(?: months?)?$/;

/** Cents from `$12,500.00`, `12500`, `12,500.5`. */
export function readCents(text: string): number | null {
  const match = MONEY.exec(text.trim());
  if (match === null) {
    return null;
  }
  const whole = (match[1] ?? "").replaceAll(",", "");
  const cents = (match[2] ?? "").padEnd(2, "0");
  return Number(whole) * 100 + Number(cents);
}

/** Basis points from `7.25%`, `7.25`, `0%`. */
export function readBps(text: string): number | null {
  const match = RATE.exec(text.trim());
  if (match === null) {
    return null;
  }
  return Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
}

/** Months from `36 months`, `1 month`, `36`. */
export function readMonths(text: string): number | null {
  const match = MONTHS.exec(text.trim());
  return match === null ? null : Number(match[1]);
}

/** Names match whatever their case and their spacing. */
export function sameText(one: string, other: string): boolean {
  const squeeze = (text: string) => text.trim().replace(/\s+/g, " ").toLowerCase();
  return squeeze(one) === squeeze(other);
}

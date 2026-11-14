// The time, as your app should read it. The sandbox freezes it, so the cases can name exact times:
// `CLOCK_NOW` in your environment says what time it is, in whole seconds since the Unix epoch.
// Without it, this reads the real clock, as a real service would.

const MS_PER_SECOND = 1000;

export function now(): Date {
  const frozen = process.env.CLOCK_NOW;
  return frozen === undefined ? new Date() : new Date(Number(frozen) * MS_PER_SECOND);
}

// A moment as the answers write it, in UTC and to the second: `2027-03-01T12:00:30Z`.
export function timestamp(moment: Date): string {
  return moment.toISOString().replace(/\.\d{3}Z$/, "Z");
}

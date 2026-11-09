// The time, as your app should read it. The sandbox freezes it: the graded webhooks were signed once,
// so `CLOCK_NOW` in your environment says what time it is, in whole seconds since the Unix epoch.
// Without it, this reads the real clock, as a real service would.

const MS_PER_SECOND = 1000;

export function nowSeconds(): number {
  const frozen = process.env.CLOCK_NOW;
  return frozen === undefined ? Math.floor(Date.now() / MS_PER_SECOND) : Number(frozen);
}

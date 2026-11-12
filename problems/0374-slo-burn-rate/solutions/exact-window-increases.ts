// Every counter keeps its samples in time order. The increase over a window walks the samples
// inside it and adds each step, counting a drop as a restart from zero. A histogram is one such
// counter per bucket. SLOs, burn rates and alerts are ratios of increases, kept as exact fractions
// and compared by cross-multiplying.

interface Slo {
  good: string;
  total: string;
  met: number;
  outOf: number;
  window: number;
}

interface Alert {
  severity: string;
  longWindow: number;
  shortWindow: number;
  above: number;
  below: number;
}

function gcd(a: number, b: number): number {
  a = Math.abs(a);
  b = Math.abs(b);
  while (b !== 0) [a, b] = [b, a % b];
  return a;
}

// `p/q` in lowest terms with q > 0, or `p` for a whole number.
function fraction(numerator: number, denominator: number): string {
  if (denominator < 0) [numerator, denominator] = [-numerator, -denominator];
  const common = gcd(numerator, denominator);
  numerator /= common;
  denominator /= common;
  return denominator === 1 ? `${numerator}` : `${numerator}/${denominator}`;
}

function parseFraction(text: string): [number, number] {
  const slash = text.indexOf("/");
  return slash < 0 ? [Number(text), 1] : [Number(text.slice(0, slash)), Number(text.slice(slash + 1))];
}

// The first index whose time is at least `time`.
function lowerBound(times: number[], time: number): number {
  let low = 0;
  let high = times.length;
  while (low < high) {
    const mid = (low + high) >> 1;
    if (times[mid] < time) low = mid + 1;
    else high = mid;
  }
  return low;
}

export class SloMonitor {
  private times = new Map<string, number[]>();
  private values = new Map<string, number[]>();
  private bounds = new Map<string, number[]>();
  private slos = new Map<string, Slo>();
  private alerts = new Map<string, Alert[]>();

  // Level 1
  scrape(series: string, timestamp: number, value: number): string {
    const times = this.times.get(series) ?? [];
    if (times.length > 0 && timestamp <= times[times.length - 1]) return "out-of-order";
    times.push(timestamp);
    this.times.set(series, times);
    const values = this.values.get(series) ?? [];
    values.push(value);
    this.values.set(series, values);
    return "ok";
  }

  scrapeSeries(series: string, start: number, step: number, values: number[]): number {
    let stored = 0;
    values.forEach((value, i) => {
      if (this.scrape(series, start + i * step, value) === "ok") stored++;
    });
    return stored;
  }

  increase(series: string, start: number, end: number): number {
    const [times, values] = this.window(series, start, end);
    if (times.length < 2) return -1;
    let total = 0;
    for (let i = 1; i < values.length; i++) {
      total += values[i] >= values[i - 1] ? values[i] - values[i - 1] : values[i];
    }
    return total;
  }

  rate(series: string, start: number, end: number): string {
    const [times] = this.window(series, start, end);
    if (times.length < 2) return "";
    return fraction(this.increase(series, start, end), times[times.length - 1] - times[0]);
  }

  resets(series: string, start: number, end: number): number {
    const [, values] = this.window(series, start, end);
    let drops = 0;
    for (let i = 1; i < values.length; i++) if (values[i] < values[i - 1]) drops++;
    return drops;
  }

  // Level 2
  scrapeHistogram(name: string, timestamp: number, bounds: number[], counts: number[]): string {
    const times = this.times.get(`${name}:le=inf`) ?? [];
    if (times.length > 0 && timestamp <= times[times.length - 1]) return "out-of-order";
    this.bounds.set(name, bounds);
    bounds.forEach((bound, i) => this.scrape(`${name}:le=${bound}`, timestamp, counts[i]));
    this.scrape(`${name}:le=inf`, timestamp, counts[bounds.length]);
    return "ok";
  }

  fractionWithin(name: string, threshold: number, start: number, end: number): string {
    const counts = this.buckets(name, start, end);
    if (counts === null) return "";
    const index = this.bounds.get(name)!.indexOf(threshold);
    return index < 0 ? "" : fraction(counts[index], counts[counts.length - 1]);
  }

  quantile(name: string, q: string, start: number, end: number): string {
    const counts = this.buckets(name, start, end);
    if (counts === null) return "";
    const [top, bottom] = parseFraction(q);
    const bounds = this.bounds.get(name)!;
    const total = counts[counts.length - 1];
    // The rank is q * total; the first bucket whose count reaches it holds the quantile.
    const index = counts.findIndex((count) => count * bottom >= top * total);
    if (index === bounds.length) return `${bounds[bounds.length - 1]}`;
    const lower = index > 0 ? bounds[index - 1] : 0;
    const before = index > 0 ? counts[index - 1] : 0;
    const inside = counts[index] - before;
    const numerator = lower * bottom * inside + (bounds[index] - lower) * (top * total - bottom * before);
    return fraction(numerator, bottom * inside);
  }

  // Level 3
  defineSlo(name: string, goodSeries: string, totalSeries: string, objective: string, window: number): string {
    if (this.slos.has(name)) return "duplicate";
    const [met, outOf] = parseFraction(objective);
    if (!(met > 0 && met < outOf)) return "bad-objective";
    this.slos.set(name, { good: goodSeries, total: totalSeries, met, outOf, window });
    this.alerts.set(name, []);
    return "ok";
  }

  sli(name: string, at: number): string {
    const slo = this.slos.get(name);
    const counts = slo === undefined ? null : this.counts(slo, at, slo.window);
    return counts === null ? "" : fraction(counts[1] - counts[0], counts[1]);
  }

  budgetRemaining(name: string, at: number): string {
    const slo = this.slos.get(name);
    const left = slo === undefined ? null : this.left(slo, at);
    return left === null ? "" : fraction(left[0], left[1]);
  }

  burnRate(name: string, at: number, lookback: number): string {
    const slo = this.slos.get(name);
    const counts = slo === undefined ? null : this.counts(slo, at, lookback);
    if (slo === undefined || counts === null) return "";
    return fraction(counts[0] * slo.outOf, counts[1] * (slo.outOf - slo.met));
  }

  timeToExhaustion(name: string, at: number, lookback: number): number {
    const slo = this.slos.get(name);
    const left = slo === undefined ? null : this.left(slo, at);
    if (slo === undefined || left === null) return -1;
    if (left[0] <= 0) return 0;
    const recent = this.counts(slo, at, lookback);
    if (recent === null || recent[0] === 0) return -1;
    const [bad, total] = this.counts(slo, at, slo.window)!;
    const [recentBad, recentTotal] = recent;
    // remaining * window / burn rate; the products can pass 2^53, so they are BigInts.
    const spare = BigInt(slo.outOf - slo.met);
    const numerator =
      BigInt(slo.window) * (BigInt(total) * spare - BigInt(bad) * BigInt(slo.outOf)) * BigInt(recentTotal);
    const denominator = BigInt(total) * BigInt(recentBad) * BigInt(slo.outOf);
    return Number(numerator / denominator);
  }

  // Level 4
  addAlert(slo: string, severity: string, longWindow: number, shortWindow: number, threshold: string): string {
    const alerts = this.alerts.get(slo);
    if (alerts === undefined) return "unknown-slo";
    if (alerts.some((alert) => alert.severity === severity)) return "duplicate";
    if (longWindow <= 0 || shortWindow < 0 || shortWindow >= longWindow) return "bad-windows";
    const [above, below] = parseFraction(threshold);
    alerts.push({ severity, longWindow, shortWindow, above, below });
    return "ok";
  }

  firing(slo: string, at: number): string[] {
    const found = this.slos.get(slo);
    if (found === undefined) return [];
    return this.alerts.get(slo)!.filter((alert) => this.fires(found, alert, at)).map((alert) => alert.severity);
  }

  timeline(slo: string, start: number, end: number, step: number): string[] {
    const found = this.slos.get(slo);
    if (found === undefined) return [];
    const alerts = this.alerts.get(slo)!;
    const state = alerts.map(() => false);
    const events: string[] = [];
    for (let at = start; at <= end; at += step) {
      alerts.forEach((alert, i) => {
        const now = this.fires(found, alert, at);
        if (now !== state[i]) {
          events.push(`${at} ${alert.severity} ${now ? "start" : "stop"}`);
          state[i] = now;
        }
      });
    }
    return events;
  }

  // Helpers
  private window(series: string, start: number, end: number): [number[], number[]] {
    const times = this.times.get(series) ?? [];
    const values = this.values.get(series) ?? [];
    const low = lowerBound(times, start);
    const high = lowerBound(times, end + 1);
    return [times.slice(low, high), values.slice(low, high)];
  }

  // The increase of every bucket over the window, or null when the window has no requests.
  private buckets(name: string, start: number, end: number): number[] | null {
    const bounds = this.bounds.get(name);
    if (bounds === undefined) return null;
    const labels = [...bounds.map(String), "inf"];
    const counts = labels.map((label) => this.increase(`${name}:le=${label}`, start, end));
    return counts[counts.length - 1] > 0 ? counts : null;
  }

  // [bad, total] over [at - span, at], or null without requests.
  private counts(slo: Slo, at: number, span: number): [number, number] | null {
    const total = this.increase(slo.total, at - span, at);
    const good = this.increase(slo.good, at - span, at);
    if (total <= 0 || good < 0) return null;
    return [total - good, total];
  }

  // The share of the budget left, as [numerator, denominator].
  private left(slo: Slo, at: number): [number, number] | null {
    const counts = this.counts(slo, at, slo.window);
    if (counts === null) return null;
    const spare = slo.outOf - slo.met;
    return [counts[1] * spare - counts[0] * slo.outOf, counts[1] * spare];
  }

  private burnsAbove(slo: Slo, at: number, span: number, alert: Alert): boolean {
    const counts = this.counts(slo, at, span);
    if (counts === null) return false;
    return counts[0] * slo.outOf * alert.below > alert.above * counts[1] * (slo.outOf - slo.met);
  }

  private fires(slo: Slo, alert: Alert, at: number): boolean {
    if (!this.burnsAbove(slo, at, alert.longWindow, alert)) return false;
    return alert.shortWindow === 0 || this.burnsAbove(slo, at, alert.shortWindow, alert);
  }
}

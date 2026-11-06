import { Decimal } from "#support";

const RATE_POINT_PLACES = 6; // a rate is per 1,000,000 tokens, so dividing only moves the point
const NO_AMOUNT = "-";

function tokenTotals(models: string[], tokens: number[][]): Map<string, number[]> {
  const totals = new Map<string, number[]>();
  models.forEach((model, line) => {
    const total = totals.get(model) ?? [0, 0, 0];
    tokens[line].forEach((count, column) => {
      total[column] += count;
    });
    totals.set(model, total);
  });
  return totals;
}

function costOf(tokens: number[], rates: Decimal[]): Decimal {
  const [inputTokens, cachedTokens, outputTokens] = tokens;
  const [inputRate, cachedRate, outputRate] = rates;
  return new Decimal(inputTokens - cachedTokens)
    .times(inputRate)
    .plus(new Decimal(cachedTokens).times(cachedRate))
    .plus(new Decimal(outputTokens).times(outputRate))
    .movePointLeft(RATE_POINT_PLACES)
    .round(2, "HALF_UP");
}

function sameTotals(a: number[], b: number[]): boolean {
  return a.every((count, column) => count === b[column]);
}

function statusOf(
  tokens: number[] | undefined,
  computed: Decimal | undefined,
  reported: number[] | undefined,
  charged: Decimal | undefined,
  tolerance: Decimal,
): string {
  if (tokens === undefined) {
    return "not-in-log";
  }
  if (computed === undefined) {
    return "unpriced-model"; // it has calls, so only a missing price leaves no computed cost
  }
  if (reported === undefined || charged === undefined) {
    return "missing-from-report";
  }
  if (!sameTotals(tokens, reported)) {
    return "token-mismatch";
  }
  return computed.minus(charged).abs().gt(tolerance) ? "cost-mismatch" : "ok";
}

function amount(value: Decimal | undefined): string {
  return value === undefined ? NO_AMOUNT : value.toFixed(2);
}

export function reconcileUsage(
  priceModels: string[],
  prices: Decimal[][],
  callModels: string[],
  callTokens: number[][],
  reportedModels: string[],
  reportedTokens: number[][],
  reportedCosts: Decimal[],
  tolerance: Decimal,
): string[][] {
  const ratesOf = new Map(priceModels.map((model, row) => [model, prices[row]]));
  const logged = tokenTotals(callModels, callTokens);
  const reported = tokenTotals(reportedModels, reportedTokens);
  const charged = new Map<string, Decimal>();
  reportedModels.forEach((model, line) => {
    charged.set(model, (charged.get(model) ?? new Decimal(0)).plus(reportedCosts[line]));
  });

  const models = [...new Set([...logged.keys(), ...reported.keys()])].sort();
  return models.map((model) => {
    const tokens = logged.get(model);
    const rates = ratesOf.get(model);
    const cost = charged.get(model);
    const computed = tokens !== undefined && rates !== undefined ? costOf(tokens, rates) : undefined;
    const status = statusOf(tokens, computed, reported.get(model), cost, tolerance);
    return [model, status, amount(computed), amount(cost)];
  });
}

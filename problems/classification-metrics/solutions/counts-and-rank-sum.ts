const SCALE = 1_000_000;
const UNDEFINED_AUC = -1;

interface ClassMetrics {
  counts: number[]; // TP, FP, FN, TN
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  auc: number;
}

/** To 6 decimal places, a value exactly halfway going up. */
function round6(value: number): number {
  return Math.floor(value * SCALE + 0.5) / SCALE;
}

function ratio(numerator: number, denominator: number): number {
  return denominator === 0 ? 0 : numerator / denominator;
}

function mean(values: number[]): number {
  return values.reduce((total, value) => total + value, 0) / values.length;
}

/** Each ratio is 0 when its denominator is 0. F1 written with counts is the harmonic mean
 * 2PR / (P + R), and it is 0 exactly when that sum is 0. */
function precisionRecallF1(tp: number, fp: number, fn: number): number[] {
  return [ratio(tp, tp + fp), ratio(tp, tp + fn), ratio(2 * tp, 2 * tp + fp + fn)];
}

/** The Mann-Whitney count: the share of (positive, negative) pairs in which the positive scores
 * higher, a tied pair counting one half. Ranking all scores once and giving tied scores the
 * average of their ranks counts exactly that. */
function auc(isPositive: boolean[], classScores: number[]): number {
  const positives = isPositive.filter((truth) => truth).length;
  const negatives = isPositive.length - positives;
  if (positives === 0 || negatives === 0) {
    return UNDEFINED_AUC;
  }
  const order = classScores.map((_, index) => index).sort((a, b) => classScores[a] - classScores[b]);
  // Twice the rank sum of the positives, so that average ranks stay whole numbers.
  let twiceRankSum = 0;
  let start = 0;
  while (start < order.length) {
    let end = start;
    while (end + 1 < order.length && classScores[order[end + 1]] === classScores[order[start]]) {
      end += 1;
    }
    let tiedPositives = 0;
    for (let position = start; position <= end; position += 1) {
      if (isPositive[order[position]]) {
        tiedPositives += 1;
      }
    }
    // Ranks start + 1 to end + 1 share their average, (start + end + 2) / 2.
    twiceRankSum += (start + end + 2) * tiedPositives;
    start = end + 1;
  }
  const twiceWins = twiceRankSum - positives * (positives + 1);
  return twiceWins / (2 * positives * negatives);
}

function classMetrics(isPositive: boolean[], classScores: number[], threshold: number): ClassMetrics {
  let tp = 0;
  let fp = 0;
  let fn = 0;
  isPositive.forEach((truth, index) => {
    const saysYes = classScores[index] >= threshold;
    if (truth && saysYes) {
      tp += 1;
    } else if (saysYes) {
      fp += 1;
    } else if (truth) {
      fn += 1;
    }
  });
  const tn = isPositive.length - tp - fp - fn;
  const [precision, recall, f1] = precisionRecallF1(tp, fp, fn);
  return {
    counts: [tp, fp, fn, tn],
    accuracy: (tp + tn) / isPositive.length,
    precision,
    recall,
    f1,
    auc: auc(isPositive, classScores),
  };
}

export function classificationMetrics(labels: number[], scores: number[][], threshold: number): number[][] {
  const classCount = scores[0].length;
  const perClass: ClassMetrics[] = [];
  for (let target = 0; target < classCount; target += 1) {
    perClass.push(
      classMetrics(
        labels.map((label) => label === target),
        scores.map((row) => row[target]),
        threshold,
      ),
    );
  }
  const rows = perClass.map((m) => [
    ...m.counts,
    ...[m.accuracy, m.precision, m.recall, m.f1, m.auc].map(round6),
  ]);

  const definedAucs = perClass.map((m) => m.auc).filter((value) => value !== UNDEFINED_AUC);
  rows.push(
    [
      mean(perClass.map((m) => m.precision)),
      mean(perClass.map((m) => m.recall)),
      mean(perClass.map((m) => m.f1)),
      mean(definedAucs),
    ].map(round6),
  );

  const total = (column: number) => perClass.reduce((sum, m) => sum + m.counts[column], 0);
  rows.push(precisionRecallF1(total(0), total(1), total(2)).map(round6));
  return rows;
}

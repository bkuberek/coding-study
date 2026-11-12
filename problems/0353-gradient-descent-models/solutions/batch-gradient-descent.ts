const SCALE = 1_000_000;
const EPSILON = 1e-7;

type Rows = number[][];
type Scaler = { means: number[]; scales: number[] };

interface StopResult {
  bestStep: number;
  stepsRun: number;
  trainError: number;
  validationError: number;
  weights: number[];
}

/** To 6 decimal places, a value exactly halfway going up. */
function round6(value: number): number {
  return Math.floor(value * SCALE + 0.5) / SCALE;
}

function total(values: number[]): number {
  let sum = 0;
  for (const value of values) {
    sum += value;
  }
  return sum;
}

/** The bias plus the weighted features, added in feature order. */
function predict(row: number[], weights: number[]): number {
  let sum = weights[0];
  row.forEach((value, j) => {
    sum += weights[j + 1] * value;
  });
  return sum;
}

function mse(features: Rows, targets: number[], weights: number[]): number {
  let sum = 0;
  features.forEach((row, i) => {
    const error = predict(row, weights) - targets[i];
    sum += error * error;
  });
  return sum / targets.length;
}

/** (2 / n) * sum of error * input, where the bias's input is always 1. */
function mseGradient(features: Rows, targets: number[], weights: number[]): number[] {
  const sums = new Array<number>(weights.length).fill(0);
  features.forEach((row, i) => {
    const error = predict(row, weights) - targets[i];
    sums[0] += error;
    row.forEach((value, j) => {
      sums[j + 1] += error * value;
    });
  });
  return sums.map((sum) => (2 * sum) / targets.length);
}

/** strength * the sum of the squared weights, the bias left out. */
function penalty(weights: number[], strength: number): number {
  let sum = 0;
  for (let j = 1; j < weights.length; j += 1) {
    sum += weights[j] * weights[j];
  }
  return strength * sum;
}

function ridgeGradient(features: Rows, targets: number[], weights: number[], strength: number): number[] {
  const gradient = mseGradient(features, targets, weights);
  for (let j = 1; j < weights.length; j += 1) {
    gradient[j] += 2 * strength * weights[j];
  }
  return gradient;
}

/** Every weight moves at once, against the gradient computed before the move. */
function step(weights: number[], gradient: number[], learningRate: number): number[] {
  return weights.map((weight, j) => weight - learningRate * gradient[j]);
}

function zeros(features: Rows): number[] {
  return new Array<number>(features[0].length + 1).fill(0);
}

function fitRidge(features: Rows, targets: number[], learningRate: number, steps: number, strength: number): number[] {
  let weights = zeros(features);
  for (let t = 0; t < steps; t += 1) {
    weights = step(weights, ridgeGradient(features, targets, weights, strength), learningRate);
  }
  return weights;
}

function sigmoid(z: number): number {
  return 1 / (1 + Math.exp(-z));
}

function logLoss(features: Rows, targets: number[], weights: number[]): number {
  let sum = 0;
  features.forEach((row, i) => {
    const p = Math.min(Math.max(sigmoid(predict(row, weights)), EPSILON), 1 - EPSILON);
    sum -= targets[i] === 1 ? Math.log(p) : Math.log(1 - p);
  });
  return sum / targets.length;
}

/** (1 / n) * sum of (p - y) * input, with the unclipped probability p. */
function logLossGradient(features: Rows, targets: number[], weights: number[]): number[] {
  const sums = new Array<number>(weights.length).fill(0);
  features.forEach((row, i) => {
    const error = sigmoid(predict(row, weights)) - targets[i];
    sums[0] += error;
    row.forEach((value, j) => {
      sums[j + 1] += error * value;
    });
  });
  return sums.map((sum) => sum / targets.length);
}

/** Consecutive blocks; the first count % folds blocks hold one example more. */
function foldBounds(count: number, folds: number): number[][] {
  const size = Math.floor(count / folds);
  const extra = count % folds;
  const bounds: number[][] = [];
  let start = 0;
  for (let fold = 0; fold < folds; fold += 1) {
    const end = start + size + (fold < extra ? 1 : 0);
    bounds.push([start, end]);
    start = end;
  }
  return bounds;
}

/** Each column's mean and population standard deviation, 1 in place of a 0 deviation. */
function fitScalerOn(features: Rows): Scaler {
  const count = features.length;
  const means: number[] = [];
  const scales: number[] = [];
  for (let j = 0; j < features[0].length; j += 1) {
    const column = features.map((row) => row[j]);
    const mean = total(column) / count;
    let spread = 0;
    for (const value of column) {
      spread += (value - mean) * (value - mean);
    }
    const deviation = Math.sqrt(spread / count);
    means.push(mean);
    scales.push(deviation > 0 ? deviation : 1);
  }
  return { means, scales };
}

function standardize(features: Rows, scaler: Scaler): Rows {
  return features.map((row) => row.map((value, j) => (value - scaler.means[j]) / scaler.scales[j]));
}

export class LinearModels {
  private readonly features: Rows;
  private readonly targets: number[];

  constructor(features: number[][], targets: number[]) {
    this.features = features.map((row) => [...row]);
    this.targets = [...targets];
  }

  // Level 1
  linearLoss(weights: number[]): number {
    return round6(mse(this.features, this.targets, weights));
  }

  linearGradient(weights: number[]): number[] {
    return mseGradient(this.features, this.targets, weights).map(round6);
  }

  trainLinear(learningRate: number, steps: number): number[][] {
    return this.train(
      (weights) => mse(this.features, this.targets, weights),
      (weights) => mseGradient(this.features, this.targets, weights),
      learningRate,
      steps,
    );
  }

  // Level 2
  logisticLoss(weights: number[]): number {
    return round6(logLoss(this.features, this.targets, weights));
  }

  logisticGradient(weights: number[]): number[] {
    return logLossGradient(this.features, this.targets, weights).map(round6);
  }

  trainLogistic(learningRate: number, steps: number): number[][] {
    return this.train(
      (weights) => logLoss(this.features, this.targets, weights),
      (weights) => logLossGradient(this.features, this.targets, weights),
      learningRate,
      steps,
    );
  }

  // Level 3
  trainRidge(learningRate: number, steps: number, strength: number): number[][] {
    return this.train(
      (weights) => mse(this.features, this.targets, weights) + penalty(weights, strength),
      (weights) => ridgeGradient(this.features, this.targets, weights, strength),
      learningRate,
      steps,
    );
  }

  crossValidate(learningRate: number, steps: number, strength: number, folds: number): number[][] {
    const errors = this.foldErrors(learningRate, steps, strength, folds);
    const means = [0, 1].map((column) => total(errors.map((row) => row[column])) / folds);
    return [...errors, means].map((row) => row.map(round6));
  }

  chooseStrength(learningRate: number, steps: number, strengths: number[], folds: number): number[] {
    let best: number[] = [];
    for (const strength of strengths) {
      const errors = this.foldErrors(learningRate, steps, strength, folds);
      const mean = round6(total(errors.map((row) => row[1])) / folds);
      if (best.length === 0 || mean < best[1]) {
        best = [strength, mean];
      }
    }
    return best;
  }

  // Level 4
  fitScaler(validationCount: number): number[][] {
    const { means, scales } = fitScalerOn(this.features.slice(0, this.features.length - validationCount));
    return [means.map(round6), scales.map(round6)];
  }

  earlyStop(learningRate: number, maxSteps: number, patience: number, validationCount: number): number[] {
    const split = this.features.length - validationCount;
    const result = this.runEarlyStop(
      fitScalerOn(this.features.slice(0, split)),
      learningRate,
      maxSteps,
      patience,
      validationCount,
    );
    return [
      result.bestStep,
      result.stepsRun,
      ...[result.trainError, result.validationError, ...result.weights].map(round6),
    ];
  }

  leakageCheck(learningRate: number, maxSteps: number, patience: number, validationCount: number): number[] {
    const split = this.features.length - validationCount;
    const honest = this.runEarlyStop(
      fitScalerOn(this.features.slice(0, split)),
      learningRate,
      maxSteps,
      patience,
      validationCount,
    );
    const leaky = this.runEarlyStop(fitScalerOn(this.features), learningRate, maxSteps, patience, validationCount);
    return [honest.bestStep, round6(honest.validationError), leaky.bestStep, round6(leaky.validationError)];
  }

  // Shared
  /** One row per state, from the zero weights to the last step: [loss, bias, weights...]. */
  private train(
    loss: (weights: number[]) => number,
    gradient: (weights: number[]) => number[],
    learningRate: number,
    steps: number,
  ): number[][] {
    let weights = zeros(this.features);
    const rows = [[loss(weights), ...weights].map(round6)];
    for (let t = 0; t < steps; t += 1) {
      weights = step(weights, gradient(weights), learningRate);
      rows.push([loss(weights), ...weights].map(round6));
    }
    return rows;
  }

  /** [training MSE, validation MSE] of each fold, trained from zero on the other folds. */
  private foldErrors(learningRate: number, steps: number, strength: number, folds: number): number[][] {
    return foldBounds(this.features.length, folds).map(([start, end]) => {
      const trainX = [...this.features.slice(0, start), ...this.features.slice(end)];
      const trainY = [...this.targets.slice(0, start), ...this.targets.slice(end)];
      const weights = fitRidge(trainX, trainY, learningRate, steps, strength);
      return [
        mse(trainX, trainY, weights),
        mse(this.features.slice(start, end), this.targets.slice(start, end), weights),
      ];
    });
  }

  /** Train on the standardized training part, watching the validation error after each step, and
   * keep the weights of the best step. Stop after `patience` steps without a new best. */
  private runEarlyStop(
    scaler: Scaler,
    learningRate: number,
    maxSteps: number,
    patience: number,
    validationCount: number,
  ): StopResult {
    const split = this.features.length - validationCount;
    const rows = standardize(this.features, scaler);
    const trainX = rows.slice(0, split);
    const trainY = this.targets.slice(0, split);
    const validX = rows.slice(split);
    const validY = this.targets.slice(split);
    let weights = zeros(rows);
    let bestStep = 0;
    let bestRounded = 0;
    let bestWeights = weights;
    let waited = 0;
    let stepsRun = 0;
    while (stepsRun < maxSteps && waited < patience) {
      stepsRun += 1;
      weights = step(weights, mseGradient(trainX, trainY, weights), learningRate);
      const error = round6(mse(validX, validY, weights));
      if (bestStep === 0 || error < bestRounded) {
        bestStep = stepsRun;
        bestRounded = error;
        bestWeights = weights;
        waited = 0;
      } else {
        waited += 1;
      }
    }
    return {
      bestStep,
      stepsRun,
      trainError: mse(trainX, trainY, bestWeights),
      validationError: mse(validX, validY, bestWeights),
      weights: bestWeights,
    };
  }
}

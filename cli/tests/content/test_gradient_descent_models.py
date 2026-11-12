"""gradient-descent-models promises that its hidden cases catch the classic mistakes of training
linear models by gradient descent: a gradient without its factor 2 or with one too many, weights
updated one at a time or rounded between steps, a missing starting row, a log loss in the wrong
base or without clipping,
a penalized bias, folds cut the wrong way or trained from the last fold's weights, a strength
chosen on training error, a sample standard deviation, a scaler fitted on the validation part, and
early stopping that counts patience wrong, returns the last weights or compares unrounded errors.
These tests replay every case against a model of the class written from the statement, which must
give every expected output, and against that model with one mistake planted at a time, which some
hidden case must fail. A mistake that crashes fails its case, as a thrown exception does in the
grader."""

import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0353-gradient-descent-models"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
TOLERANCE = 1e-9
EPSILON = 1e-7

Rows = list[list[float]]
Weights = list[float]


class Model:
    """The class as the statement words it, one rule per method, so that each mistake below
    overrides a single method. Sums run left to right in plain loops."""

    def __init__(self, features: Rows, targets: list[float]) -> None:
        self.features = [list(row) for row in features]
        self.targets = list(targets)

    # --- shared rules
    def rounded(self, value: float) -> float:
        return math.floor(value * 1_000_000 + 0.5) / 1_000_000

    def z(self, row: list[float], weights: Weights) -> float:
        value = weights[0]
        for j, x in enumerate(row):
            value += weights[j + 1] * x
        return value

    def zeros(self, features: Rows) -> Weights:
        return [0.0] * (len(features[0]) + 1)

    def moved(self, weights: Weights, slope: Callable[[Weights], Weights], rate: float) -> Weights:
        gradient = slope(weights)
        return [w - rate * g for w, g in zip(weights, gradient, strict=True)]

    def history(
        self, loss: Callable[[Weights], float], slope: Callable[[Weights], Weights], rate, steps
    ) -> Rows:
        weights = self.zeros(self.features)
        rows = [[loss(weights), *weights]]
        for _ in range(steps):
            weights = self.moved(weights, slope, rate)
            rows.append([loss(weights), *weights])
        return [[self.rounded(v) for v in row] for row in rows]

    def slopes(self, features: Rows, misses: list[float], factor: float) -> Weights:
        sums = [0.0] * (len(features[0]) + 1)
        for row, miss in zip(features, misses, strict=True):
            sums[0] += miss
            for j, x in enumerate(row):
                sums[j + 1] += miss * x
        return [factor * total / len(misses) for total in sums]

    # --- level 1
    def mean(self, values: list[float]) -> float:
        total = 0.0
        for value in values:
            total += value
        return total / len(values)

    def mse(self, features: Rows, targets: list[float], weights: Weights) -> float:
        return self.mean(
            [(self.z(r, weights) - y) ** 2 for r, y in zip(features, targets, strict=True)]
        )

    def mse_slope(self, features: Rows, targets: list[float], weights: Weights) -> Weights:
        misses = [self.z(r, weights) - y for r, y in zip(features, targets, strict=True)]
        return self.slopes(features, misses, 2.0)

    def linear_loss(self, weights: Weights) -> float:
        return self.rounded(self.mse(self.features, self.targets, weights))

    def linear_gradient(self, weights: Weights) -> Weights:
        return [self.rounded(g) for g in self.mse_slope(self.features, self.targets, weights)]

    def train_linear(self, rate: float, steps: int) -> Rows:
        return self.history(
            lambda w: self.mse(self.features, self.targets, w),
            lambda w: self.mse_slope(self.features, self.targets, w),
            rate,
            steps,
        )

    # --- level 2
    def probability(self, z: float) -> float:
        return 1 / (1 + math.exp(-z))

    def clipped(self, p: float) -> float:
        return min(max(p, EPSILON), 1 - EPSILON)

    def ln(self, value: float) -> float:
        return math.log(value)

    def log_loss(self, weights: Weights) -> float:
        costs = []
        for row, y in zip(self.features, self.targets, strict=True):
            p = self.clipped(self.probability(self.z(row, weights)))
            costs.append(-self.ln(p) if y == 1 else -self.ln(1 - p))
        return self.mean(costs)

    def log_slope(self, weights: Weights) -> Weights:
        misses = [
            self.probability(self.z(r, weights)) - y
            for r, y in zip(self.features, self.targets, strict=True)
        ]
        return self.slopes(self.features, misses, 1.0)

    def logistic_loss(self, weights: Weights) -> float:
        return self.rounded(self.log_loss(weights))

    def logistic_gradient(self, weights: Weights) -> Weights:
        return [self.rounded(g) for g in self.log_slope(weights)]

    def train_logistic(self, rate: float, steps: int) -> Rows:
        return self.history(self.log_loss, self.log_slope, rate, steps)

    # --- level 3
    def penalty(self, weights: Weights, strength: float) -> float:
        total = 0.0
        for w in weights[1:]:
            total += w * w
        return strength * total

    def penalty_slope(self, weights: Weights, strength: float) -> Weights:
        return [0.0] + [2 * strength * w for w in weights[1:]]

    def ridge_slope(
        self, features: Rows, targets: list[float], weights: Weights, strength: float
    ) -> Weights:
        mse = self.mse_slope(features, targets, weights)
        extra = self.penalty_slope(weights, strength)
        return [mse[0]] + [a + b for a, b in zip(mse[1:], extra[1:], strict=True)]

    def train_ridge(self, rate: float, steps: int, strength: float) -> Rows:
        return self.history(
            lambda w: self.mse(self.features, self.targets, w) + self.penalty(w, strength),
            lambda w: self.ridge_slope(self.features, self.targets, w, strength),
            rate,
            steps,
        )

    def fold_sizes(self, count: int, folds: int) -> list[int]:
        return [count // folds + (1 if f < count % folds else 0) for f in range(folds)]

    def fold_indexes(self, count: int, folds: int) -> list[list[int]]:
        blocks, start = [], 0
        for size in self.fold_sizes(count, folds):
            blocks.append(list(range(start, start + size)))
            start += size
        return blocks

    def start_of_fold(self, previous: Weights | None, features: Rows) -> Weights:
        return self.zeros(features)

    def validation_error(
        self, features: Rows, targets: list[float], weights: Weights, strength: float
    ) -> float:
        return self.mse(features, targets, weights)

    def fold_errors(self, rate: float, steps: int, strength: float, folds: int) -> Rows:
        errors, weights = [], None
        for block in self.fold_indexes(len(self.targets), folds):
            inside = set(block)
            train_x = [r for i, r in enumerate(self.features) if i not in inside]
            train_y = [y for i, y in enumerate(self.targets) if i not in inside]
            weights = self.start_of_fold(weights, train_x)
            for _ in range(steps):
                weights = self.moved(
                    weights,
                    lambda w, x=train_x, y=train_y: self.ridge_slope(x, y, w, strength),
                    rate,
                )
            valid_x = [self.features[i] for i in block]
            valid_y = [self.targets[i] for i in block]
            errors.append(
                [
                    self.mse(train_x, train_y, weights),
                    self.validation_error(valid_x, valid_y, weights, strength),
                ]
            )
        return errors

    def fold_mean(self, values: list[float], sizes: list[int]) -> float:
        return self.mean(values)

    def cross_validate(self, rate: float, steps: int, strength: float, folds: int) -> Rows:
        errors = self.fold_errors(rate, steps, strength, folds)
        sizes = self.fold_sizes(len(self.targets), folds)
        means = [self.fold_mean([row[c] for row in errors], sizes) for c in (0, 1)]
        return [[self.rounded(v) for v in row] for row in [*errors, means]]

    def scored_column(self) -> int:
        return 1

    def beats(self, candidate: float, best: float) -> bool:
        return candidate < best

    def choose_strength(
        self, rate: float, steps: int, strengths: list[float], folds: int
    ) -> list[float]:
        best: list[float] = []
        sizes = self.fold_sizes(len(self.targets), folds)
        for strength in strengths:
            errors = self.fold_errors(rate, steps, strength, folds)
            score = self.rounded(
                self.fold_mean([row[self.scored_column()] for row in errors], sizes)
            )
            if not best or self.beats(score, best[1]):
                best = [strength, score]
        return [best[0], self.mean_validation(rate, steps, best[0], folds)]

    def mean_validation(self, rate: float, steps: int, strength: float, folds: int) -> float:
        errors = self.fold_errors(rate, steps, strength, folds)
        return self.rounded(self.mean([row[1] for row in errors]))

    # --- level 4
    def parts(self, held_out: int) -> tuple[list[int], list[int]]:
        cut = len(self.targets) - held_out
        return list(range(cut)), list(range(cut, len(self.targets)))

    def spread(self, column: list[float], mean: float) -> float:
        return math.sqrt(self.mean([(x - mean) ** 2 for x in column]))

    def scaler_of(self, indexes: list[int]) -> tuple[list[float], list[float]]:
        means, scales = [], []
        for j in range(len(self.features[0])):
            column = [self.features[i][j] for i in indexes]
            mean = self.mean(column)
            deviation = self.spread(column, mean)
            means.append(mean)
            scales.append(deviation if deviation > 0 else 1.0)
        return means, scales

    def honest_rows(self, held_out: int) -> list[int]:
        return self.parts(held_out)[0]

    def fit_scaler(self, held_out: int) -> Rows:
        means, scales = self.scaler_of(self.parts(held_out)[0])
        return [[self.rounded(m) for m in means], [self.rounded(s) for s in scales]]

    def improved(self, error: float, best: float) -> bool:
        return self.rounded(error) < self.rounded(best)

    def out_of_patience(self, waited: int, patience: int) -> bool:
        return waited >= patience

    def kept(self, best: Weights, last: Weights) -> Weights:
        return best

    def stop_early(self, scaler_rows: list[int], rate, max_steps, patience, held_out) -> tuple:
        means, scales = self.scaler_of(scaler_rows)
        table = [
            [(x - m) / s for x, m, s in zip(row, means, scales, strict=True)]
            for row in self.features
        ]
        train, valid = self.parts(held_out)
        tx, ty = [table[i] for i in train], [self.targets[i] for i in train]
        vx, vy = [table[i] for i in valid], [self.targets[i] for i in valid]
        weights = self.zeros(tx)
        best: tuple[int, float, Weights] | None = None
        waited = taken = 0
        while taken < max_steps and not self.out_of_patience(waited, patience):
            taken += 1
            weights = self.moved(weights, lambda w: self.mse_slope(tx, ty, w), rate)
            error = self.mse(vx, vy, weights)
            if best is None or self.improved(error, best[1]):
                best, waited = (taken, error, weights), 0
            else:
                waited += 1
        assert best is not None
        chosen = self.kept(best[2], weights)
        return best[0], taken, self.mse(tx, ty, chosen), self.mse(vx, vy, chosen), chosen

    def early_stop(self, rate: float, max_steps: int, patience: int, held_out: int) -> list:
        step, taken, train, valid, weights = self.stop_early(
            self.honest_rows(held_out), rate, max_steps, patience, held_out
        )
        return [step, taken, *(self.rounded(v) for v in (train, valid, *weights))]

    def leakage_check(self, rate: float, max_steps: int, patience: int, held_out: int) -> list:
        honest = self.stop_early(self.honest_rows(held_out), rate, max_steps, patience, held_out)
        everyone = list(range(len(self.targets)))
        leaky = self.stop_early(everyone, rate, max_steps, patience, held_out)
        return [honest[0], self.rounded(honest[3]), leaky[0], self.rounded(leaky[3])]


# ------------------------------------------------------------------ level 1 mistakes
class GradientWithoutTheTwo(Model):
    """Forgets that the slope of a square is twice the miss."""

    def mse_slope(self, features: Rows, targets: list[float], weights: Weights) -> Weights:
        return [g / 2 for g in super().mse_slope(features, targets, weights)]


class LossIsASum(Model):
    """Adds the squared misses up without dividing by n."""

    def mse(self, features: Rows, targets: list[float], weights: Weights) -> float:
        return super().mse(features, targets, weights) * len(targets)


class WeightsUpdatedOneByOne(Model):
    """Moves each weight in turn, computing the next slope from the weights already moved."""

    def moved(self, weights: Weights, slope: Callable[[Weights], Weights], rate: float) -> Weights:
        weights = list(weights)
        for j in range(len(weights)):
            weights[j] -= rate * slope(weights)[j]
        return weights


class BiasNeverMoves(Model):
    """Trains the feature weights and leaves the bias at 0."""

    def moved(self, weights: Weights, slope: Callable[[Weights], Weights], rate: float) -> Weights:
        return [0.0, *super().moved(weights, slope, rate)[1:]]


class NoStartingRow(Model):
    """Leaves out the row of the zero weights."""

    def history(self, loss, slope, rate, steps) -> Rows:
        return super().history(loss, slope, rate, steps)[1:]


class LossOfThePreviousWeights(Model):
    """Records each step's loss before the weights move."""

    def history(self, loss, slope, rate, steps) -> Rows:
        rows = super().history(loss, slope, rate, steps)
        return [[*rows[max(0, i - 1)][:1], *row[1:]] for i, row in enumerate(rows)]


class WeightsRoundedEveryStep(Model):
    """Rounds the weights to 6 decimals after every step, not only in the rows."""

    def moved(self, weights: Weights, slope: Callable[[Weights], Weights], rate: float) -> Weights:
        return [self.rounded(w) for w in super().moved(weights, slope, rate)]


class DigitsCutNotRounded(Model):
    """Drops the digits after the sixth instead of rounding."""

    def rounded(self, value: float) -> float:
        return math.floor(value * 1_000_000) / 1_000_000


# ------------------------------------------------------------------ level 2 mistakes
class LogBaseTwo(Model):
    """Measures the log loss in bits."""

    def ln(self, value: float) -> float:
        return math.log2(value)


class NoClipping(Model):
    """Takes the logarithm of the raw probability."""

    def clipped(self, p: float) -> float:
        return p


class TinyEpsilon(Model):
    """Clips at 1e-15 instead of 1e-7."""

    def clipped(self, p: float) -> float:
        return min(max(p, 1e-15), 1 - 1e-15)


class LogisticGradientWithTheTwo(Model):
    """Copies the factor 2 of the squared error into the log loss's gradient."""

    def log_slope(self, weights: Weights) -> Weights:
        return [2 * g for g in super().log_slope(weights)]


class SquaredErrorOnProbabilities(Model):
    """Trains the probabilities on the squared error instead of the log loss."""

    def log_slope(self, weights: Weights) -> Weights:
        misses = []
        for row, y in zip(self.features, self.targets, strict=True):
            p = self.probability(self.z(row, weights))
            misses.append((p - y) * p * (1 - p))
        return self.slopes(self.features, misses, 2.0)


class SigmoidOfMinusZ(Model):
    """Flips the sign inside the sigmoid."""

    def probability(self, z: float) -> float:
        return 1 / (1 + math.exp(z))


# ------------------------------------------------------------------ level 3 mistakes
class BiasPenalized(Model):
    """Penalizes the bias like the other weights."""

    def penalty(self, weights: Weights, strength: float) -> float:
        return super().penalty(weights, strength) + strength * weights[0] ** 2

    def ridge_slope(
        self, features: Rows, targets: list[float], weights: Weights, strength: float
    ) -> Weights:
        slope = super().ridge_slope(features, targets, weights, strength)
        return [slope[0] + 2 * strength * weights[0], *slope[1:]]


class PenaltySlopeWithoutTheTwo(Model):
    """Gives the penalty a slope of strength * w."""

    def penalty_slope(self, weights: Weights, strength: float) -> Weights:
        return [g / 2 for g in super().penalty_slope(weights, strength)]


class RidgeRowsWithoutThePenalty(Model):
    """Reports the plain MSE in the training rows of the ridge model."""

    def penalty(self, weights: Weights, strength: float) -> float:
        return 0.0


class FoldsByRemainder(Model):
    """Deals the examples out to the folds like cards: example i to fold i mod k."""

    def fold_indexes(self, count: int, folds: int) -> list[list[int]]:
        return [list(range(f, count, folds)) for f in range(folds)]


class ExtraExamplesInTheLastFolds(Model):
    """Gives the larger blocks to the last folds."""

    def fold_sizes(self, count: int, folds: int) -> list[int]:
        return super().fold_sizes(count, folds)[::-1]


class MeanWeightedByFoldSize(Model):
    """Averages the folds by their number of examples."""

    def fold_mean(self, values: list[float], sizes: list[int]) -> float:
        return sum(v * s for v, s in zip(values, sizes, strict=True)) / sum(sizes)


class WeightsCarriedAcrossFolds(Model):
    """Starts each fold from the weights the previous fold ended with."""

    def start_of_fold(self, previous: Weights | None, features: Rows) -> Weights:
        return list(previous) if previous is not None else self.zeros(features)


class ValidationErrorWithPenalty(Model):
    """Adds the penalty to the validation error."""

    def validation_error(
        self, features: Rows, targets: list[float], weights: Weights, strength: float
    ) -> float:
        return self.mse(features, targets, weights) + self.penalty(weights, strength)


class ChosenByTrainingError(Model):
    """Picks the strength with the lowest training error."""

    def scored_column(self) -> int:
        return 0


class LastStrengthWinsATie(Model):
    """Keeps the later of two strengths with the same error."""

    def beats(self, candidate: float, best: float) -> bool:
        return candidate <= best


# ------------------------------------------------------------------ level 4 mistakes
class SampleStandardDeviation(Model):
    """Divides the spread by m - 1."""

    def spread(self, column: list[float], mean: float) -> float:
        if len(column) < 2:
            return 0.0
        return math.sqrt(sum((x - mean) ** 2 for x in column) / (len(column) - 1))


class ScaleZeroForAConstantFeature(Model):
    """Divides a constant feature by its deviation of 0."""

    def scaler_of(self, indexes: list[int]) -> tuple[list[float], list[float]]:
        means, scales = super().scaler_of(indexes)
        for j, scale in enumerate(scales):
            column = [self.features[i][j] for i in indexes]
            if scale == 1.0 and self.spread(column, means[j]) == 0:
                scales[j] = 0.0
        return means, scales


class ScalerFittedOnEverything(Model):
    """Fits the scaler on all the examples, validation part included."""

    def honest_rows(self, held_out: int) -> list[int]:
        return list(range(len(self.targets)))


class ValidationFromTheFront(Model):
    """Sets the first examples aside instead of the last."""

    def parts(self, held_out: int) -> tuple[list[int], list[int]]:
        return list(range(held_out, len(self.targets))), list(range(held_out))


class LastWeightsReturned(Model):
    """Returns the weights of the last step instead of the best one."""

    def kept(self, best: Weights, last: Weights) -> Weights:
        return last


class PatienceOneTooMany(Model):
    """Waits for one more step without a new best before stopping."""

    def out_of_patience(self, waited: int, patience: int) -> bool:
        return waited > patience


class EqualErrorIsAnImprovement(Model):
    """Takes an error equal to the best as a new best."""

    def improved(self, error: float, best: float) -> bool:
        return self.rounded(error) <= self.rounded(best)


class UnroundedComparison(Model):
    """Compares the validation errors before rounding."""

    def improved(self, error: float, best: float) -> bool:
        return error < best


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def close(actual: Any, expected: Any) -> bool:
    """The problem's comparator: every number within 1e-9, relative above 1."""
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(close(a, e) for a, e in zip(actual, expected, strict=True))
        )
    if expected is None:
        return actual is None
    return isinstance(actual, int | float) and abs(actual - expected) <= TOLERANCE * max(
        1, abs(expected)
    )


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return close(outputs(model_type, case), case["expected"])
    except (ArithmeticError, ValueError, IndexError, KeyError, TypeError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert close(outputs(Model, case), case["expected"])


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_a_visible_case_shows_the_leaky_scaler_changing_the_result():
    shown = [
        got
        for case in CASES
        if case.get("visible")
        for op, got in zip(case["ops"], case["expected"], strict=True)
        if op == "leakageCheck"
    ]
    assert any(honest_step != leaky_step for honest_step, _, leaky_step, _ in shown)

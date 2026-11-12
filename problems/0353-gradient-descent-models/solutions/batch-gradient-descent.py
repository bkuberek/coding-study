from collections.abc import Callable, Iterable
from math import exp, floor, log, sqrt
from typing import NamedTuple

SCALE = 1_000_000
EPSILON = 1e-7

Rows = list[list[float]]
Scaler = tuple[list[float], list[float]]


class StopResult(NamedTuple):
    best_step: int
    steps_run: int
    train_error: float
    validation_error: float
    weights: list[float]


def _round(value: float) -> float:
    """To 6 decimal places, a value exactly halfway going up."""
    return floor(value * SCALE + 0.5) / SCALE


def _total(values: Iterable[float]) -> float:
    """Left to right in a plain loop: since Python 3.12 the built-in sum of floats compensates for
    rounding, so it can differ from other languages in the last bit."""
    total = 0.0
    for value in values:
        total += value
    return total


def _predict(row: list[float], weights: list[float]) -> float:
    """The bias plus the weighted features, added in feature order."""
    total = weights[0]
    for weight, value in zip(weights[1:], row, strict=True):
        total += weight * value
    return total


def _mse(features: Rows, targets: list[float], weights: list[float]) -> float:
    total = 0.0
    for row, target in zip(features, targets, strict=True):
        error = _predict(row, weights) - target
        total += error * error
    return total / len(targets)


def _mse_gradient(features: Rows, targets: list[float], weights: list[float]) -> list[float]:
    """(2 / n) * sum of error * input, where the bias's input is always 1."""
    sums = [0.0] * len(weights)
    for row, target in zip(features, targets, strict=True):
        error = _predict(row, weights) - target
        sums[0] += error
        for j, value in enumerate(row, start=1):
            sums[j] += error * value
    return [2 * total / len(targets) for total in sums]


def _penalty(weights: list[float], strength: float) -> float:
    """strength * the sum of the squared weights, the bias left out."""
    total = 0.0
    for weight in weights[1:]:
        total += weight * weight
    return strength * total


def _ridge_gradient(
    features: Rows, targets: list[float], weights: list[float], strength: float
) -> list[float]:
    gradient = _mse_gradient(features, targets, weights)
    for j in range(1, len(weights)):
        gradient[j] += 2 * strength * weights[j]
    return gradient


def _step(weights: list[float], gradient: list[float], learning_rate: float) -> list[float]:
    """Every weight moves at once, against the gradient computed before the move."""
    return [weight - learning_rate * slope for weight, slope in zip(weights, gradient, strict=True)]


def _fit_ridge(
    features: Rows, targets: list[float], learning_rate: float, steps: int, strength: float
) -> list[float]:
    weights = [0.0] * (len(features[0]) + 1)
    for _ in range(steps):
        weights = _step(
            weights, _ridge_gradient(features, targets, weights, strength), learning_rate
        )
    return weights


def _sigmoid(z: float) -> float:
    return 1 / (1 + exp(-z))


def _log_loss(features: Rows, targets: list[float], weights: list[float]) -> float:
    total = 0.0
    for row, target in zip(features, targets, strict=True):
        p = min(max(_sigmoid(_predict(row, weights)), EPSILON), 1 - EPSILON)
        total -= log(p) if target == 1 else log(1 - p)
    return total / len(targets)


def _log_loss_gradient(features: Rows, targets: list[float], weights: list[float]) -> list[float]:
    """(1 / n) * sum of (p - y) * input, with the unclipped probability p."""
    sums = [0.0] * len(weights)
    for row, target in zip(features, targets, strict=True):
        error = _sigmoid(_predict(row, weights)) - target
        sums[0] += error
        for j, value in enumerate(row, start=1):
            sums[j] += error * value
    return [total / len(targets) for total in sums]


def _fold_bounds(count: int, folds: int) -> list[tuple[int, int]]:
    """Consecutive blocks; the first count % folds blocks hold one example more."""
    size, extra = divmod(count, folds)
    bounds = []
    start = 0
    for fold in range(folds):
        end = start + size + (1 if fold < extra else 0)
        bounds.append((start, end))
        start = end
    return bounds


def _scaler(features: Rows) -> Scaler:
    """Each column's mean and population standard deviation, 1 in place of a 0 deviation."""
    count = len(features)
    means = []
    scales = []
    for column in zip(*features, strict=True):
        mean = _total(column) / count
        spread = 0.0
        for value in column:
            spread += (value - mean) * (value - mean)
        deviation = sqrt(spread / count)
        means.append(mean)
        scales.append(deviation if deviation > 0 else 1.0)
    return means, scales


def _standardize(features: Rows, means: list[float], scales: list[float]) -> Rows:
    return [
        [(value - mean) / scale for value, mean, scale in zip(row, means, scales, strict=True)]
        for row in features
    ]


class LinearModels:
    def __init__(self, features: list[list[float]], targets: list[float]) -> None:
        self._features = [list(row) for row in features]
        self._targets = list(targets)

    # Level 1
    def linear_loss(self, weights: list[float]) -> float:
        return _round(_mse(self._features, self._targets, weights))

    def linear_gradient(self, weights: list[float]) -> list[float]:
        return [_round(slope) for slope in _mse_gradient(self._features, self._targets, weights)]

    def train_linear(self, learning_rate: float, steps: int) -> list[list[float]]:
        return self._train(
            lambda weights: _mse(self._features, self._targets, weights),
            lambda weights: _mse_gradient(self._features, self._targets, weights),
            learning_rate,
            steps,
        )

    # Level 2
    def logistic_loss(self, weights: list[float]) -> float:
        return _round(_log_loss(self._features, self._targets, weights))

    def logistic_gradient(self, weights: list[float]) -> list[float]:
        return [
            _round(slope) for slope in _log_loss_gradient(self._features, self._targets, weights)
        ]

    def train_logistic(self, learning_rate: float, steps: int) -> list[list[float]]:
        return self._train(
            lambda weights: _log_loss(self._features, self._targets, weights),
            lambda weights: _log_loss_gradient(self._features, self._targets, weights),
            learning_rate,
            steps,
        )

    # Level 3
    def train_ridge(self, learning_rate: float, steps: int, strength: float) -> list[list[float]]:
        return self._train(
            lambda weights: (
                _mse(self._features, self._targets, weights) + _penalty(weights, strength)
            ),
            lambda weights: _ridge_gradient(self._features, self._targets, weights, strength),
            learning_rate,
            steps,
        )

    def cross_validate(
        self, learning_rate: float, steps: int, strength: float, folds: int
    ) -> list[list[float]]:
        errors = self._fold_errors(learning_rate, steps, strength, folds)
        means = [_total(column) / folds for column in zip(*errors, strict=True)]
        return [[_round(error) for error in row] for row in [*errors, means]]

    def choose_strength(
        self, learning_rate: float, steps: int, strengths: list[float], folds: int
    ) -> list[float]:
        best: list[float] = []
        for strength in strengths:
            errors = self._fold_errors(learning_rate, steps, strength, folds)
            mean = _round(_total([validation for _, validation in errors]) / folds)
            if not best or mean < best[1]:
                best = [strength, mean]
        return best

    # Level 4
    def fit_scaler(self, validation_count: int) -> list[list[float]]:
        means, scales = _scaler(self._features[: len(self._features) - validation_count])
        return [[_round(mean) for mean in means], [_round(scale) for scale in scales]]

    def early_stop(
        self, learning_rate: float, max_steps: int, patience: int, validation_count: int
    ) -> list[float]:
        split = len(self._features) - validation_count
        result = self._early_stop(
            _scaler(self._features[:split]), learning_rate, max_steps, patience, validation_count
        )
        return [float(result.best_step), float(result.steps_run)] + [
            _round(value)
            for value in (result.train_error, result.validation_error, *result.weights)
        ]

    def leakage_check(
        self, learning_rate: float, max_steps: int, patience: int, validation_count: int
    ) -> list[float]:
        split = len(self._features) - validation_count
        honest = self._early_stop(
            _scaler(self._features[:split]), learning_rate, max_steps, patience, validation_count
        )
        leaky = self._early_stop(
            _scaler(self._features), learning_rate, max_steps, patience, validation_count
        )
        return [
            float(honest.best_step),
            _round(honest.validation_error),
            float(leaky.best_step),
            _round(leaky.validation_error),
        ]

    # Shared
    def _train(
        self,
        loss: Callable[[list[float]], float],
        gradient: Callable[[list[float]], list[float]],
        learning_rate: float,
        steps: int,
    ) -> list[list[float]]:
        """One row per state, from the zero weights to the last step: [loss, bias, weights...]."""
        weights = [0.0] * (len(self._features[0]) + 1)
        rows = [self._row(loss(weights), weights)]
        for _ in range(steps):
            weights = _step(weights, gradient(weights), learning_rate)
            rows.append(self._row(loss(weights), weights))
        return rows

    @staticmethod
    def _row(loss: float, weights: list[float]) -> list[float]:
        return [_round(loss)] + [_round(weight) for weight in weights]

    def _fold_errors(
        self, learning_rate: float, steps: int, strength: float, folds: int
    ) -> list[list[float]]:
        """[training MSE, validation MSE] of each fold, trained from zero on the other folds."""
        errors = []
        for start, end in _fold_bounds(len(self._features), folds):
            train_x = self._features[:start] + self._features[end:]
            train_y = self._targets[:start] + self._targets[end:]
            weights = _fit_ridge(train_x, train_y, learning_rate, steps, strength)
            errors.append(
                [
                    _mse(train_x, train_y, weights),
                    _mse(self._features[start:end], self._targets[start:end], weights),
                ]
            )
        return errors

    def _early_stop(
        self,
        scaler: Scaler,
        learning_rate: float,
        max_steps: int,
        patience: int,
        validation_count: int,
    ) -> StopResult:
        """Train on the standardized training part, watching the validation error after each step,
        and keep the weights of the best step. Stop after `patience` steps without a new best."""
        split = len(self._features) - validation_count
        rows = _standardize(self._features, *scaler)
        train_x, train_y = rows[:split], self._targets[:split]
        valid_x, valid_y = rows[split:], self._targets[split:]
        weights = [0.0] * (len(rows[0]) + 1)
        best_step, best_rounded, best_weights = 0, 0.0, weights
        waited = 0
        step = 0
        while step < max_steps and waited < patience:
            step += 1
            weights = _step(weights, _mse_gradient(train_x, train_y, weights), learning_rate)
            error = _round(_mse(valid_x, valid_y, weights))
            if best_step == 0 or error < best_rounded:
                best_step, best_rounded, best_weights = step, error, weights
                waited = 0
            else:
                waited += 1
        return StopResult(
            best_step,
            step,
            _mse(train_x, train_y, best_weights),
            _mse(valid_x, valid_y, best_weights),
            best_weights,
        )

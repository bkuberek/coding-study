from math import floor
from typing import NamedTuple

SCALE = 1_000_000
UNDEFINED_AUC = -1.0


class ClassReport(NamedTuple):
    tp: int
    fp: int
    fn: int
    tn: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    auc: float


def classification_metrics(
    labels: list[int], scores: list[list[float]], threshold: float
) -> list[list[float]]:
    reports = [
        _class_report(
            [label == target for label in labels], [row[target] for row in scores], threshold
        )
        for target in range(len(scores[0]))
    ]
    rows = [
        [float(r.tp), float(r.fp), float(r.fn), float(r.tn)]
        + [_round(rate) for rate in (r.accuracy, r.precision, r.recall, r.f1, r.auc)]
        for r in reports
    ]
    defined_aucs = [r.auc for r in reports if r.auc != UNDEFINED_AUC]
    macro = [
        _mean([r.precision for r in reports]),
        _mean([r.recall for r in reports]),
        _mean([r.f1 for r in reports]),
        _mean(defined_aucs),
    ]
    rows.append([_round(rate) for rate in macro])
    micro = _precision_recall_f1(
        sum(r.tp for r in reports), sum(r.fp for r in reports), sum(r.fn for r in reports)
    )
    rows.append([_round(rate) for rate in micro])
    return rows


def _class_report(
    is_positive: list[bool], class_scores: list[float], threshold: float
) -> ClassReport:
    """One class asked as a yes-or-no question: its four counts and its rates."""
    outcomes = [
        (truth, score >= threshold) for truth, score in zip(is_positive, class_scores, strict=True)
    ]
    tp = outcomes.count((True, True))
    fp = outcomes.count((False, True))
    fn = outcomes.count((True, False))
    tn = len(outcomes) - tp - fp - fn
    precision, recall, f1 = _precision_recall_f1(tp, fp, fn)
    return ClassReport(
        tp,
        fp,
        fn,
        tn,
        (tp + tn) / len(outcomes),
        precision,
        recall,
        f1,
        _auc(is_positive, class_scores),
    )


def _precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Each ratio is 0 when its denominator is 0. F1 written with counts is the harmonic mean
    2PR / (P + R), and it is 0 exactly when that sum is 0."""
    return _ratio(tp, tp + fp), _ratio(tp, tp + fn), _ratio(2 * tp, 2 * tp + fp + fn)


def _auc(is_positive: list[bool], class_scores: list[float]) -> float:
    """The Mann-Whitney count: the share of (positive, negative) pairs in which the positive
    scores higher, a tied pair counting one half. Ranking all scores once and giving tied
    scores the average of their ranks counts exactly that."""
    positives = sum(is_positive)
    negatives = len(is_positive) - positives
    if positives == 0 or negatives == 0:
        return UNDEFINED_AUC
    order = sorted(range(len(class_scores)), key=lambda index: class_scores[index])
    # Twice the rank sum of the positives, so that average ranks stay whole numbers.
    twice_rank_sum = 0
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and class_scores[order[end + 1]] == class_scores[order[start]]:
            end += 1
        tied_positives = sum(1 for index in order[start : end + 1] if is_positive[index])
        # Ranks start + 1 to end + 1 share their average, (start + end + 2) / 2.
        twice_rank_sum += (start + end + 2) * tied_positives
        start = end + 1
    twice_wins = twice_rank_sum - positives * (positives + 1)
    return twice_wins / (2 * positives * negatives)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _mean(values: list[float]) -> float:
    # A plain loop: since Python 3.12 the built-in sum of floats compensates for rounding, so it
    # can differ from other languages in the last bit.
    total = 0.0
    for value in values:
        total += value
    return total / len(values)


def _round(value: float) -> float:
    """To 6 decimal places, a value exactly halfway going up."""
    return floor(value * SCALE + 0.5) / SCALE

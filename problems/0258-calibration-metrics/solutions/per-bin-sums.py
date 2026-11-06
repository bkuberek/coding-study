from math import floor


def calibration_report(
    probabilities: list[float],
    outcomes: list[bool],
    slice_names: list[str],
    report_slices: list[str],
    bin_count: int,
) -> list[list[float]]:
    predictions = list(zip(probabilities, outcomes, strict=True))
    by_slice: dict[str, list[tuple[float, bool]]] = {}
    for prediction, name in zip(predictions, slice_names, strict=True):
        by_slice.setdefault(name, []).append(prediction)
    rows = [_row(predictions, bin_count)]
    rows.extend(_row(by_slice.get(name, []), bin_count) for name in report_slices)
    return rows


def _row(group: list[tuple[float, bool]], bin_count: int) -> list[float]:
    size = len(group)
    if size == 0:
        return [0.0, 0.0, 0.0]
    probability_sums = [0.0] * bin_count
    true_counts = [0] * bin_count
    squared_error = 0.0
    for probability, outcome in group:
        index = min(floor(probability * bin_count), bin_count - 1)
        probability_sums[index] += probability
        true_counts[index] += outcome
        squared_error += (probability - outcome) ** 2
    # (bin size / N) * |sum / bin size - trues / bin size| is |sum - trues| / N: the bin size
    # cancels, so an empty bin needs no special case.
    gaps = (abs(total - trues) for total, trues in zip(probability_sums, true_counts, strict=True))
    return [float(size), sum(gaps) / size, squared_error / size]

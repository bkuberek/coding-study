"""Three forecasters on the same thirty days: is it calibrated, and how good is it overall?

The days fall into three kinds. On ten days of the first kind it rained twice, on ten of the
second five times, and on ten of the third eight times. Each forecaster states one probability of
rain per kind of day.
"""

import math

rained = {"first": 2, "second": 5, "third": 8}  # rainy days out of 10 of each kind
forecasters = {
    "honest": {"first": 0.2, "second": 0.5, "third": 0.8},
    "base rate": {"first": 0.5, "second": 0.5, "third": 0.5},
    "overconfident": {"first": 0.01, "second": 0.5, "third": 0.99},
}

for name, said in forecasters.items():
    groups: dict[float, list[int]] = {}  # stated probability -> [days, rainy days]
    brier = log_loss = 0.0
    for kind, rainy in rained.items():
        p, dry = said[kind], 10 - rainy
        days, wet = groups.get(p, [0, 0])
        groups[p] = [days + 10, wet + rainy]
        brier += rainy * (1 - p) ** 2 + dry * p**2
        log_loss += rainy * -math.log(p) + dry * -math.log(1 - p)
    # How far each stated probability is from how often it rained when it was said.
    gap = sum(days * abs(p - wet / days) for p, (days, wet) in groups.items())
    print(f"{name:13}  calibration error {gap / 30:.3f}  Brier {brier / 30:.3f}  "
          f"log loss {log_loss / 30:.3f}")

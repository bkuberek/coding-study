"""RFC 6298's retransmission timeout, computed over a run of round-trip samples.

SRTT follows the typical round trip and RTTVAR how much it varies; the timeout, RTO, is SRTT plus
four times RTTVAR, and never less than one second. An expiry doubles RTO, and the next sample
brings it back down. Times are in seconds.
"""

ALPHA, BETA, K = 1 / 8, 1 / 4, 4
G = 0.001  # clock granularity: a 1 ms clock
MIN_RTO, MAX_RTO = 1.0, 60.0  # 60 s is the lowest cap that RFC 6298 allows


class Estimator:
    def __init__(self) -> None:
        self.srtt: float | None = None
        self.rttvar = 0.0
        self.rto = 1.0  # before any sample

    def sample(self, r: float) -> None:
        if self.srtt is None:
            self.srtt, self.rttvar = r, r / 2
        else:
            self.rttvar = (1 - BETA) * self.rttvar + BETA * abs(self.srtt - r)  # old SRTT here
            self.srtt = (1 - ALPHA) * self.srtt + ALPHA * r
        self.rto = min(max(self.srtt + max(G, K * self.rttvar), MIN_RTO), MAX_RTO)

    def back_off(self) -> None:
        self.rto = min(2 * self.rto, MAX_RTO)


EVENTS = [0.80, 0.82, 0.79, 0.81, 0.80, 1.60, 0.81, "expiry", "expiry", 0.85]
estimator = Estimator()
print("event     SRTT    RTTVAR  RTO")
print(f"start     -       -       {estimator.rto:.3f}")
for event in EVENTS:
    if event == "expiry":
        estimator.back_off()
        label = "expiry"
    else:
        estimator.sample(float(event))
        label = f"R={event:.2f}"
    print(f"{label:<9} {estimator.srtt:.3f}   {estimator.rttvar:.3f}   {estimator.rto:.3f}")

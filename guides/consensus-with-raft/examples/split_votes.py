"""A model of why Raft draws its election timeouts at random.

Five servers stop hearing from their leader at the same moment, and each waits for its own
election timeout. The first to time out asks the others for their votes, and the request takes
5 ms to arrive. A server whose timeout runs out before that request arrives stands too, and the
votes split; then every server waits a new timeout and the round starts again. The model only
counts rounds until one server times out alone; it is far simpler than Raft's real rules.
"""

import random

SERVERS, DELAY_MS, TRIALS, GIVE_UP = 5, 5, 1000, 20


def rounds_until_leader(rng: random.Random, low: int, high: int) -> int | None:
    for round_number in range(1, GIVE_UP + 1):
        timeouts = sorted(rng.randrange(low, high + 1) for _ in range(SERVERS))
        if timeouts[1] >= timeouts[0] + DELAY_MS:  # the first candidate's request wins the race
            return round_number
    return None


rng = random.Random(2014)
print(f"{'election timeouts':<22} {'first round':>11} {'mean rounds':>11} {'no leader':>9}")
for low, high in [(150, 150), (150, 175), (150, 300)]:
    results = [rounds_until_leader(rng, low, high) for _ in range(TRIALS)]
    elected = [r for r in results if r is not None]
    first = sum(1 for r in elected if r == 1)
    mean = f"{sum(elected) / len(elected):.2f}" if elected else "-"
    label = f"{low} ms for all" if low == high else f"{low} to {high} ms"
    print(f"{label:<22} {first:>11} {mean:>11} {TRIALS - len(elected):>9}")

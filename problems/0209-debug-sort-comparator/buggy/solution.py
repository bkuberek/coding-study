"""Debug: Leaderboard Comparator. Some tests fail: find the bug and fix it."""

from functools import cmp_to_key

SCORE_EPSILON = 1


def _compare(a: tuple[str, int], b: tuple[str, int]) -> int:
    name_a, score_a = a
    name_b, score_b = b
    if abs(score_a - score_b) <= SCORE_EPSILON:
        return -1 if name_a < name_b else 1
    return score_b - score_a


def rank_players(names: list[str], scores: list[int]) -> list[str]:
    players = list(zip(names, scores))
    players.sort(key=cmp_to_key(_compare))
    return [name for name, _ in players]

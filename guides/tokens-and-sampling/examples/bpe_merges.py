"""Byte pair encoding on a toy corpus: learn merges from word counts, then split words with them."""

from collections import Counter

END = "_"  # ends every word, so a piece at the end of a word differs from the same letters inside one


def merge(symbols: tuple[str, ...], pair: tuple[str, str]) -> tuple[str, ...]:
    merged, i = [], 0
    while i < len(symbols):
        if symbols[i : i + 2] == pair:
            merged.append(symbols[i] + symbols[i + 1])
            i += 2
        else:
            merged.append(symbols[i])
            i += 1
    return tuple(merged)


def learn(word_counts: dict[str, int], rounds: int) -> list[tuple[str, str]]:
    words = {(*word, END): count for word, count in word_counts.items()}
    merges = []
    for _ in range(rounds):
        pairs: Counter[tuple[str, str]] = Counter()
        for symbols, count in words.items():
            for pair in zip(symbols, symbols[1:]):
                pairs[pair] += count
        best = max(sorted(pairs), key=pairs.__getitem__)  # equal counts: the first pair in sorted order
        merges.append(best)
        words = {merge(symbols, best): count for symbols, count in words.items()}
    return merges


def split(word: str, merges: list[tuple[str, str]]) -> list[str]:
    symbols = (*word, END)
    for pair in merges:
        symbols = merge(symbols, pair)
    return list(symbols)


corpus = {"play": 6, "played": 4, "playing": 3, "replay": 2, "stay": 3, "staying": 2}
merges = learn(corpus, rounds=10)
print("merges, in the order learned:")
for number, (left, right) in enumerate(merges, start=1):
    print(f"  {number}. {left} + {right} -> {left + right}")

for word in ["playing", "replayed", "staged", "zebra"]:
    pieces = split(word, merges)
    print(f"{word:>9}: {len(word)} letters -> {len(pieces)} tokens {pieces}")

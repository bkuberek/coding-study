def partition_labels(s: str) -> list[int]:
    # Each letter occupies the span from its first to its last copy. Spans listed by first
    # occurrence are already sorted by start, so merging overlapping spans gives the pieces.
    first: dict[str, int] = {}
    last: dict[str, int] = {}
    for index, letter in enumerate(s):
        first.setdefault(letter, index)
        last[letter] = index
    sizes = []
    piece_start, piece_end = 0, -1
    for letter in first:  # dicts keep insertion order: letters by first occurrence
        if first[letter] > piece_end:
            if piece_end >= 0:
                sizes.append(piece_end - piece_start + 1)
            piece_start = first[letter]
        piece_end = max(piece_end, last[letter])
    sizes.append(piece_end - piece_start + 1)
    return sizes

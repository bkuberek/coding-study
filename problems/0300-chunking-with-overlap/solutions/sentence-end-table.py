import re

TOKEN = re.compile(r"[^ \t\n\r]+")
SENTENCE_ENDINGS = frozenset(".!?")
NO_SENTENCE_END = -1


def chunk_text(text: str, max_tokens: int, overlap: int) -> list[list[int]]:
    if overlap >= max_tokens:
        return []
    spans = [match.span() for match in TOKEN.finditer(text)]
    last_sentence_end = _last_sentence_end_by_token(text, spans)
    final = len(spans) - 1
    chunks: list[list[int]] = []
    first, last = 0, -1
    # The loop stops once a chunk reaches the final token, so the shared tail of the last chunk
    # never becomes a chunk of its own.
    while last < final:
        window_last = first + max_tokens - 1
        if window_last >= final:
            last = final
        elif last_sentence_end[window_last] >= first + overlap:
            last = last_sentence_end[window_last]
        else:
            last = window_last
        chunks.append([spans[first][0], spans[last][1]])
        first = last - overlap + 1
    return chunks


def _last_sentence_end_by_token(text: str, spans: list[tuple[int, int]]) -> list[int]:
    """For each token, the index of the last token at or before it that ends a sentence."""
    table: list[int] = []
    latest = NO_SENTENCE_END
    for index, (_, end) in enumerate(spans):
        if text[end - 1] in SENTENCE_ENDINGS:
            latest = index
        table.append(latest)
    return table

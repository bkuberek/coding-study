from fractions import Fraction

RELEVANT = "relevant"
AMBIGUOUS = "ambiguous"
IRRELEVANT = "irrelevant"


def _dot(a: list[int], b: list[int]) -> int:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _sentences(text: str) -> list[str]:
    """The sentences of a text, each with its period: the text is split after every period."""
    return [piece.strip() + "." for piece in text.split(".")[:-1]]


def _tokens(text: str) -> int:
    """One token per word and one per period."""
    return len(text.split(" ")) + text.count(".")


class CorrectiveRag:
    def __init__(self) -> None:
        self._passages: dict[str, tuple[list[int], str]] = {}
        self._queries: dict[str, list[int]] = {}
        self._verdicts: dict[tuple[str, str], str] = {}
        self._fallbacks: dict[str, dict[str, str]] = {}
        self._rewrites: dict[str, list[str]] = {}

    # Level 1
    def add_passage(self, passage_id: str, embedding: list[int], text: str) -> bool:
        if passage_id in self._passages:
            return False
        self._passages[passage_id] = (embedding, text)
        return True

    def add_query(self, query: str, embedding: list[int]) -> bool:
        if query in self._queries:
            return False
        self._queries[query] = embedding
        return True

    def add_verdict(self, query: str, item_id: str, verdict: str) -> bool:
        if (query, item_id) in self._verdicts:
            return False
        self._verdicts[(query, item_id)] = verdict
        return True

    def retrieve(self, query: str, k: int) -> list[list[str]]:
        return [[pid, self._verdict(query, pid)] for pid in self._top(query, k)]

    def keep_relevant(self, query: str, k: int) -> list[str]:
        return [pid for pid in self._top(query, k) if self._verdict(query, pid) == RELEVANT]

    def verdict_counts(self, query: str, k: int) -> list[int]:
        verdicts = [self._verdict(query, pid) for pid in self._top(query, k)]
        return [verdicts.count(RELEVANT), verdicts.count(AMBIGUOUS), verdicts.count(IRRELEVANT)]

    # Level 2
    def add_fallback(self, query: str, fallback_id: str, text: str) -> bool:
        items = self._fallbacks.setdefault(query, {})
        if fallback_id in items:
            return False
        items[fallback_id] = text
        return True

    def decide(self, query: str, k: int) -> str:
        return self._decision(query, self._top(query, k))

    def evidence(self, query: str, k: int) -> list[list[str]]:
        return [[item_id, text] for item_id, _, text in self._evidence(query, k)]

    # Level 3
    def add_rewrite(self, query: str, rewrite: str) -> bool:
        listed = self._rewrites.setdefault(query, [])
        if rewrite == query or rewrite in listed:
            return False
        listed.append(rewrite)
        return True

    def attempts(self, query: str, k: int, need: int, max_retries: int) -> list[list[str]]:
        tried, chosen = self._search(query, k, need, max_retries)
        return [
            [asked, self.decide(asked, k), str(count), "chosen" if index == chosen else "tried"]
            for index, (asked, count) in enumerate(tried)
        ]

    # Level 4
    def grounded_context(
        self, query: str, k: int, need: int, max_retries: int, budget: int
    ) -> list[list[str]]:
        _, rows = self._grounded(query, k, need, max_retries, budget)
        return rows

    def answer(
        self, query: str, k: int, need: int, max_retries: int, budget: int, min_support: int
    ) -> str:
        searched, rows = self._grounded(query, k, need, max_retries, budget)
        sources: dict[str, str] = {}
        for number, cite, _, _ in rows:
            sources.setdefault(number, cite)
        if len(sources) < min_support:
            return f"not enough evidence: {len(sources)} of {min_support} sources"
        lines = [f"question: {query}", f"searched: {searched}"]
        lines += [f"[{number}] {text}" for number, _, _, text in rows]
        lines.append("sources: " + ", ".join(f"[{n}] {cite}" for n, cite in sources.items()))
        return "\n".join(lines)

    # Helpers
    def _verdict(self, query: str, item_id: str) -> str:
        return self._verdicts.get((query, item_id), IRRELEVANT)

    def _top(self, query: str, k: int) -> list[str]:
        """The k best passages by cosine, compared exactly: cos * |cos| orders like the cosine,
        and with the query's length common to all, it is dot * |dot| / |p|^2 up to a constant."""
        embedding = self._queries.get(query)
        if embedding is None or not any(embedding):
            return []
        scored = []
        for pid, (vector, _) in self._passages.items():
            length = _dot(vector, vector)
            if length:
                dot = _dot(embedding, vector)
                scored.append((-Fraction(dot * abs(dot), length), pid))
        scored.sort()
        return [pid for _, pid in scored[:k]]

    def _decision(self, query: str, top: list[str]) -> str:
        verdicts = [self._verdict(query, pid) for pid in top]
        relevant, ambiguous = RELEVANT in verdicts, AMBIGUOUS in verdicts
        if relevant:
            return "refine" if ambiguous else "keep"
        return "blend" if ambiguous else "fallback"

    def _evidence(self, query: str, k: int) -> list[tuple[str, str, str]]:
        """(item id, the id it cites, text) for every piece of evidence, in order."""
        top = self._top(query, k)
        found = []
        for pid in top:
            verdict = self._verdict(query, pid)
            text = self._passages[pid][1]
            if verdict == RELEVANT:
                found.append((pid, pid, text))
            elif verdict == AMBIGUOUS:
                for number, sentence in enumerate(_sentences(text), start=1):
                    sentence_id = f"{pid}#{number}"
                    if self._verdict(query, sentence_id) == RELEVANT:
                        found.append((sentence_id, pid, sentence))
        if self._decision(query, top) in ("blend", "fallback"):
            for fid, text in self._fallbacks.get(query, {}).items():
                if self._verdict(query, fid) == RELEVANT:
                    found.append((fid, fid, text))
        return found

    def _search(
        self, query: str, k: int, need: int, max_retries: int
    ) -> tuple[list[tuple[str, int]], int]:
        """The attempts made, with their evidence counts, and the index of the chosen one."""
        candidates = [query, *self._rewrites.get(query, [])[:max_retries]]
        tried: list[tuple[str, int]] = []
        for asked in candidates:
            tried.append((asked, len(self._evidence(asked, k))))
            if tried[-1][1] >= need:
                return tried, len(tried) - 1
        best = max(range(len(tried)), key=lambda index: (tried[index][1], -index))
        return tried, best

    def _grounded(
        self, query: str, k: int, need: int, max_retries: int, budget: int
    ) -> tuple[str, list[list[str]]]:
        tried, chosen = self._search(query, k, need, max_retries)
        searched = tried[chosen][0]
        numbers: dict[str, int] = {}
        rows = []
        remaining = budget
        for _, cite, text in self._evidence(searched, k):
            tokens = _tokens(text)
            if tokens > remaining:
                break
            remaining -= tokens
            number = numbers.setdefault(cite, len(numbers) + 1)
            rows.append([str(number), cite, str(tokens), text])
        return searched, rows

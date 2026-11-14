COUNTED = 0
DUPLICATE = 1
RIVAL = 2
LOOP = 3
NONE = -1


class ReferralProgram:
    """Counted referrals form a forest: a person has at most one referrer.

    People are numbered in the order they first appear in a counted referral. The forest is kept
    in arrays (a referrer, a first and a last child, and a next sibling per person), a union-find
    answers "would this referral close a loop?" without walking up, and the totals are recounted
    in one breadth-first pass when a question needs them after a change. Nothing recurses, so a
    chain of 10^6 referrals is as safe as a flat one.
    """

    def __init__(self, bonus: int) -> None:
        self._bonus = bonus
        self._index: dict[str, int] = {}
        self._names: list[str] = []
        self._referrer: list[int] = []
        self._first: list[int] = []
        self._last: list[int] = []
        self._next: list[int] = []
        self._direct: list[int] = []
        self._set: list[int] = []
        self._size: list[int] = []
        self._totals: list[int] | None = []

    # Level 1
    def refer(self, referrer: str, referred: str) -> int:
        return self._bonus if self._apply(referrer, referred) == COUNTED else 0

    def points(self, person: str) -> int:
        at = self._index.get(person)
        return 0 if at is None else self._direct[at] * self._bonus

    def referrals_of(self, person: str) -> list[str]:
        at = self._index.get(person)
        found: list[str] = []
        child = NONE if at is None else self._first[at]
        while child != NONE:
            found.append(self._names[child])
            child = self._next[child]
        return found

    # Level 2
    def total_referrals(self, person: str) -> int:
        at = self._index.get(person)
        return 0 if at is None else self._recount()[at]

    def top_referrer(self) -> str:
        best = self.leaderboard(1)
        return best[0] if best else ""

    # Level 3
    def refer_all(self, rows: list[list[str]]) -> list[int]:
        tally = [0, 0, 0, 0]
        for referrer, referred in rows:
            tally[self._apply(referrer, referred)] += 1
        return tally

    # Level 4
    def leaderboard(self, k: int) -> list[str]:
        totals = self._recount()
        ranked = [at for at in range(len(totals)) if totals[at] > 0]
        ranked.sort(key=lambda at: (-totals[at], -self._direct[at], self._names[at]))
        return [self._names[at] for at in ranked[:k]]

    def _person(self, name: str) -> int:
        at = self._index.get(name)
        if at is None:
            at = len(self._names)
            self._index[name] = at
            self._names.append(name)
            for column in (self._referrer, self._first, self._last, self._next):
                column.append(NONE)
            self._direct.append(0)
            self._set.append(at)
            self._size.append(1)
            self._totals = None
        return at

    def _root_of(self, at: int) -> int:
        while self._set[at] != at:
            self._set[at] = self._set[self._set[at]]
            at = self._set[at]
        return at

    def _apply(self, referrer: str, referred: str) -> int:
        if referrer == referred:
            return LOOP
        known = self._index.get(referred)
        if known is not None and self._referrer[known] != NONE:
            same = self._names[self._referrer[known]] == referrer
            return DUPLICATE if same else RIVAL
        above, below = self._person(referrer), self._person(referred)
        top, bottom = self._root_of(above), self._root_of(below)
        if top == bottom:
            return LOOP
        if self._size[top] < self._size[bottom]:
            top, bottom = bottom, top
        self._set[bottom] = top
        self._size[top] += self._size[bottom]
        self._referrer[below] = above
        if self._first[above] == NONE:
            self._first[above] = below
        else:
            self._next[self._last[above]] = below
        self._last[above] = below
        self._direct[above] += 1
        self._totals = None
        return COUNTED

    def _recount(self) -> list[int]:
        if self._totals is not None:
            return self._totals
        count = len(self._names)
        order = [at for at in range(count) if self._referrer[at] == NONE]
        for at in order:
            child = self._first[at]
            while child != NONE:
                order.append(child)
                child = self._next[child]
        totals = [0] * count
        for at in reversed(order):
            above = self._referrer[at]
            if above != NONE:
                totals[above] += totals[at] + 1
        self._totals = totals
        return totals

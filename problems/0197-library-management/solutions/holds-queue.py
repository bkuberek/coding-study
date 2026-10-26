from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FinePolicy:
    per_day: int

    def fine(self, due: int, returned: int) -> int:
        return max(0, returned - due) * self.per_day


@dataclass(slots=True)
class Title:
    """All copies of one ISBN, with the members waiting for one."""

    isbn: str
    copies: int = 0
    on_loan: int = 0
    reserved: set[str] = field(default_factory=set)  # members with a copy set aside for them
    waiting: deque[str] = field(default_factory=deque)

    @property
    def free(self) -> int:
        return self.copies - self.on_loan - len(self.reserved)

    def assign_free_copies(self) -> None:
        """Invariant: a free copy never sits on the shelf while someone is waiting."""
        while self.free > 0 and self.waiting:
            self.reserved.add(self.waiting.popleft())


@dataclass(slots=True)
class Member:
    member_id: str
    max_loans: int
    loans: dict[str, int] = field(default_factory=dict)  # isbn -> due day
    fines: int = 0

    def can_borrow(self, isbn: str) -> bool:
        return self.fines == 0 and isbn not in self.loans and len(self.loans) < self.max_loans


class Library:
    def __init__(self, loan_days: int, fine_per_day: int) -> None:
        self._loan_days = loan_days
        self._fine_policy = FinePolicy(fine_per_day)
        self._titles: dict[str, Title] = {}
        self._members: dict[str, Member] = {}

    def add_book(self, isbn: str, copies: int) -> int:
        title = self._titles.setdefault(isbn, Title(isbn))
        title.copies += copies
        title.assign_free_copies()
        return title.copies

    def add_member(self, member_id: str, max_loans: int) -> bool:
        if member_id in self._members:
            return False
        self._members[member_id] = Member(member_id, max_loans)
        return True

    def checkout(self, day: int, member_id: str, isbn: str) -> int:
        member, title = self._members.get(member_id), self._titles.get(isbn)
        if member is None or title is None or not member.can_borrow(isbn):
            return -1
        if member_id in title.reserved:
            title.reserved.remove(member_id)
        elif title.free == 0:
            return -1
        title.on_loan += 1
        member.loans[isbn] = day + self._loan_days
        return member.loans[isbn]

    def return_book(self, day: int, member_id: str, isbn: str) -> int:
        member = self._members.get(member_id)
        if member is None or isbn not in member.loans:
            return -1
        fine = self._fine_policy.fine(member.loans.pop(isbn), day)
        member.fines += fine
        title = self._titles[isbn]
        title.on_loan -= 1
        title.assign_free_copies()
        return fine

    def place_hold(self, day: int, member_id: str, isbn: str) -> int:
        member, title = self._members.get(member_id), self._titles.get(isbn)
        if member is None or title is None or title.free > 0:
            return -1
        if isbn in member.loans or member_id in title.reserved or member_id in title.waiting:
            return -1
        title.waiting.append(member_id)
        return len(title.waiting)

    def cancel_hold(self, day: int, member_id: str, isbn: str) -> bool:
        title = self._titles.get(isbn)
        if title is None:
            return False
        if member_id in title.waiting:
            title.waiting.remove(member_id)
            return True
        if member_id in title.reserved:
            title.reserved.remove(member_id)
            title.assign_free_copies()
            return True
        return False

    def renew(self, day: int, member_id: str, isbn: str) -> int:
        member = self._members.get(member_id)
        if member is None or isbn not in member.loans:
            return -1
        if day > member.loans[isbn] or self._titles[isbn].waiting:
            return -1
        member.loans[isbn] += self._loan_days
        return member.loans[isbn]

    def fines(self, day: int, member_id: str) -> int:
        member = self._members.get(member_id)
        return -1 if member is None else member.fines

    def pay_fine(self, day: int, member_id: str, amount: int) -> int:
        member = self._members.get(member_id)
        if member is None:
            return -1
        member.fines = max(0, member.fines - amount)
        return member.fines

    def available(self, day: int, isbn: str) -> int:
        title = self._titles.get(isbn)
        return -1 if title is None else title.free

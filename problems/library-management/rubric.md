# Library Management: Rubric

## Responsibilities

- [ ] A title owns its copy counts, its reservations and its waiting queue, and alone decides who gets a copy that becomes free.
- [ ] A member owns their loans (title to due day) and their unpaid fines, and answers whether they may borrow.
- [ ] Fine computation lives in one fine policy, not inside `returnBook`.
- [ ] `Library` validates ids and coordinates a member and a title; it holds no queue or fine arithmetic itself.

## Extension points

- [ ] A different fine rule (a cap, grace days, member discounts) is a new fine policy; loans and holds do not change.
- [ ] Member types with different limits or loan periods change the member model only.
- [ ] Reservation expiry can be added to the title (an expiry day per reservation, checked on each call) without touching members.

## Patterns

- [ ] One invariant ("no free copy while someone waits") is enforced by a single method called after every event that can free a copy.
- [ ] The holds queue is FIFO, and reserved copies are tracked separately from the queue, so positions and availability are always consistent.
- [ ] Policies such as fines are small value objects injected into the library, making the rules explicit and replaceable.

## Testability

- [ ] Every time-dependent rule (due days, lateness, renewals) takes `day` as an argument; nothing reads a clock.
- [ ] A title can be tested alone: add copies, lend, return, hold, and check reservations and availability.
- [ ] Failures are sentinel values (`-1`, `false`), so tests check outcomes without exception handling.

## Reference design

```text
Library (facade)
 ├── titles:  isbn -> Title(copies, onLoan, reserved: member set, waiting: member queue)
 ├── members: id -> Member(maxLoans, loans: isbn -> due day, fines)
 └── FinePolicy(perDay).fine(due, returnedOn)
Title.free = copies - onLoan - |reserved|;  Title.assignFreeCopies() moves free copies to the queue's front
```

`checkout` asks the member whether it may borrow (no fines, no copy of this title, below its limit), then asks the title for a copy: the member's own reservation first, otherwise a free copy. `returnBook` removes the loan, charges the fine computed by the policy, and gives the copy back to the title, which immediately calls `assignFreeCopies`. `addBook` and `cancelHold` of a reservation call it too, so the invariant holds after every call. `placeHold` can then rely on "a free copy means nobody waits" and simply refuses when a copy is free.

Copies are not modeled individually because they are interchangeable here; a per-copy model (barcodes, condition) would replace the counts with a set of copy objects inside `Title` and change nothing outside it. The queue is a FIFO of member ids; removing a member from the middle (cancellation) is O(h), which is fine for short queues. Renewal is refused while someone waits, which keeps the queue fair without extra bookkeeping.

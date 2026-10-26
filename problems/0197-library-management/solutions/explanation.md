# Library Management: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| holds-queue | optimal | O(1) per operation; O(h) per hold placement or cancellation | O(t + m + l + h) | default answer; one invariant keeps holds and availability consistent |

Here `t` is the number of titles, `m` of members, `l` of open loans and `h` the length of a title's queue.

## Approach: holds-queue (Titles with reservations and a waiting queue)

### Intuition

Copies of a title are interchangeable, so the system does not need to track which physical copy is where; it needs to know how many are on loan, which members have one set aside, and who is waiting. That turns every question into arithmetic on one `Title` object: free copies are `copies - onLoan - reserved`.

The rules about holds all follow from one invariant: a free copy never sits on the shelf while someone is waiting. Enforce it in one method, call that method after every event that can free a copy, and the other operations become simple: if a copy is free, nobody is waiting, so `placeHold` can refuse and `checkout` can take it.

### Algorithm

1. `Title.assignFreeCopies()`: while a copy is free and the queue is not empty, move the queue's front member into `reserved`. Called after `addBook`, `returnBook` and the cancellation of a reservation.
2. `checkout(day, member, isbn)`: the member must exist, have no fines, not hold this title already and be below its loan limit. Then use the member's reservation if it has one; otherwise there must be a free copy. Increase `onLoan` and record `due = day + loanDays`.
3. `returnBook`: remove the loan (unknown: `-1`), add `max(0, day - due) * finePerDay` to the member's fines, decrease `onLoan`, and assign free copies.
4. `placeHold`: refuse when a copy is free, or when the member already has the title on loan, reserved, or in the queue; otherwise append the member and return the queue length.
5. `cancelHold`: remove the member from the queue, or give up its reservation and assign free copies.
6. `renew`: refuse when overdue or when the title's queue is not empty; otherwise add `loanDays` to the due day.
7. `fines`, `payFine` and `available` read or update one number.

### Correctness

Invariant 1: for each title, `onLoan` equals the number of members with that title in their loans, and `free >= 0`. `checkout` increases `onLoan` only after taking a reservation or seeing a free copy, and `returnBook` decreases it only for an existing loan.

Invariant 2: `free > 0` implies the queue is empty. It holds initially and is restored by `assignFreeCopies` after every event that increases `free` (new copies, a return, a released reservation). `checkout` and `placeHold` only decrease `free` or grow the queue while `free == 0`. Reservations are therefore given in queue order, which is the order holds were placed.

Fines are charged exactly once per late return, from the due day in force at that moment, so renewals move the deadline as required. A member with fines is blocked only from borrowing, as specified, and payments never push the balance below zero.

### Complexity

- Time: O(1) per operation; O(h) per hold placement or cancellation — map and set operations are O(1) on average; checking whether a member is already in a queue and removing a member from its middle scan the queue.
- Space: O(t + m + l + h) — one object per title and member, one entry per loan, and one per waiting member.

### Trade-offs

- Modeling individual copies (with barcodes) is closer to reality and needed for condition tracking or per-copy locations, but adds a copy-to-member mapping for no benefit in these rules. The title-level model can be swapped for it inside `Title` alone.
- A linked hash set for the queue would make "already waiting?" and cancellation O(1) while keeping FIFO order; with short queues the plain queue is clearer.
- Refusing renewals while anyone waits is a policy choice that keeps queues moving. A gentler policy (allow one renewal) would live in `renew` and maybe a member type.
- Reserved copies here never expire. Real libraries hold a copy for a few days; that needs an expiry day per reservation and a check (with the `day` argument) on each call, a natural follow-up.

### Pitfalls and edge cases

- New copies must serve waiting members before anyone else; forgetting to call the assignment after `addBook` leaves copies free while people wait.
- A member with a reservation and unpaid fines cannot borrow, and must keep the reservation; check the member before consuming it.
- Releasing a reservation passes the copy to the next member in line, not back to the shelf.
- The due day itself is not late: returning or renewing on it costs nothing and is allowed.
- A member cannot hold a title they already have on loan, or hold it twice.
- Fines can make several loans late at once; each return adds its own fine.

### Language notes

- Python: dataclasses with `field(default_factory=...)` for the mutable members, a `deque` for the queue, and a `free` property on `Title`.
- TypeScript: a getter for `free`, a `Set` for reservations whose `delete` returns whether the member was there (used to consume a reservation), and `shift()` on the queue, which is fine for short queues.
- Java: `Set.remove` and `Deque.remove(Object)` return booleans, which keeps `checkout` and `cancelHold` short; `Map.putIfAbsent` implements `addMember`; the fine policy is a `record`.
- Kotlin: `?: return -1` guards for every lookup, `ArrayDeque` for the queue, and `HashMap.remove(isbn) ?: return -1` fetches and deletes a loan in one step.

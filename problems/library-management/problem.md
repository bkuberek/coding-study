# Library Management

## Statement

Design the circulation system of a small library. The catalog holds titles by ISBN, each with some number of identical copies. Members borrow copies for a fixed loan period, may renew, and pay a fine for every day they are late. When every copy of a title is out, members can place a hold; returned copies are then set aside for them in the order the holds were placed.

Implement the facade class `Library`. Time is a day number passed to each call as `day`; nothing reads a clock.

## Input

- `Library(loanDays, finePerDay)`: an empty library; a loan lasts `loanDays` days and every late day costs `finePerDay`.
- `addBook(isbn, copies)`: adds copies of a title, creating it if needed.
- `addMember(memberId, maxLoans)`: registers a member who may have at most `maxLoans` books at once.
- `checkout(day, memberId, isbn)`, `returnBook(day, memberId, isbn)`: lending and returning a copy.
- `placeHold(day, memberId, isbn)`, `cancelHold(day, memberId, isbn)`: joining and leaving the queue for a title.
- `renew(day, memberId, isbn)`: extends a loan.
- `fines(day, memberId)`, `payFine(day, memberId, amount)`: the member's unpaid fines.
- `available(day, isbn)`: copies anyone may borrow right now.

Rules:

- A copy is on loan, set aside for one member (reserved), or free. A free copy is never left on the shelf while members wait: whenever a copy becomes free (a return, new copies, a cancelled reservation), it is reserved for the member at the front of the title's queue, who leaves the queue.
- A member may borrow when they have no unpaid fines, do not already have a copy of that title, and have fewer than `maxLoans` books. They get their reserved copy if they have one, otherwise a free copy. The due day is `day + loanDays`.
- Returning on day `d` a book due on day `due` adds a fine of `max(0, d - due) * finePerDay`.
- A hold is allowed only when no copy is free, and the member neither has the title on loan, nor a reserved copy, nor a hold for it already. Unpaid fines do not prevent holds.
- `cancelHold` removes the member from the queue, or gives up their reserved copy, which then goes to the next member in the queue.
- A loan can be renewed, adding `loanDays` to its due day, unless it is overdue (`day` after the due day) or someone is waiting in the title's queue.
- Days never decrease within a test; several calls may share a day.

## Output

- `addBook` returns the title's total number of copies.
- `addMember` returns `false` when the member exists.
- `checkout` returns the due day, or `-1` when any rule above prevents the loan or the member or title is unknown.
- `returnBook` returns the fine for this return (`0` when on time), or `-1` when the member does not have this title.
- `placeHold` returns the member's position in the queue, starting at 1, or `-1` when the hold is not allowed.
- `cancelHold` returns `true` when a hold or reservation was removed.
- `renew` returns the new due day, or `-1`.
- `fines` and `payFine` return the unpaid amount after the call (a payment above it only clears it), or `-1` for an unknown member.
- `available` returns the number of free copies, or `-1` for an unknown title.

## Examples

### Example 1

<!-- case: ex1 -->

`ana` borrows the only copy on day 1, due on day 15. `bob` cannot borrow it and places the first hold. `ana` returns it on day 18, three days late, so she owes 30; the copy is reserved for `bob`. `ana` cannot borrow again (fines, and the copy is not free), but `bob` can.

### Example 2

<!-- case: ex2 -->

The renewal on day 5 moves the due day from 7 to 14. The member has one loan of the one book they may have, so a second checkout fails. Returning on day 16 costs 2 late days at 5. Paying 4 leaves 6, and paying 100 clears the rest, so the member may borrow again.

## Constraints

- `1 <= loanDays <= 100` and `0 <= finePerDay <= 100`.
- `1 <= copies <= 10`, `1 <= maxLoans <= 10`, `1 <= amount <= 10^6`.
- `0 <= day <= 10^6`.
- At most 1000 calls per test. ISBNs and member ids are 1 to 13 letters or digits.

## Follow-ups

- How would a reserved copy expire if its member does not pick it up within three days?
- How would you support member types with different loan periods and fine caps?

## Hints

### Hint 1

Model a title, not individual copies: copies are identical, so counts of copies on loan and the set of reserved members are enough.

### Hint 2

Write one method on the title that moves free copies to waiting members, and call it after every change that can free a copy.

### Hint 3

That invariant (no free copy while someone waits) makes `placeHold` and `checkout` simple: if a copy is free, nobody is waiting for it.

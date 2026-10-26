# Vending Machine: Rubric

## Responsibilities

- [ ] The machine's state is one explicit value, and each public method states which states it is legal in.
- [ ] A coin box alone owns the coin counts and decides how to pay an amount; the facade never computes change itself.
- [ ] The inventory (slots with price and count) is separate from money handling.
- [ ] The return tray is the only way coins leave the machine, for change, refunds and rejected coins alike.

## Extension points

- [ ] A new payment method (card, token) adds credit without changing the coin box or the inventory.
- [ ] A different change policy (always return the inserted coins, prefer small coins) replaces the coin box's planning only.
- [ ] A new state (for example `OUT_OF_ORDER` after a fault) is one enum value and its guards, not edits scattered across unrelated code.

## Patterns

- [ ] The state machine is explicit: an enum (or State objects) with transitions in one place, rather than booleans like `inService` and `hasCredit` that can contradict each other.
- [ ] Change making plans first and commits only on success, so a failed sale leaves no partial effects.
- [ ] Change making is exact for limited coins (dynamic programming), not greedy, and documents its tie-break.

## Testability

- [ ] Every effect is observable through return values, `state`, `stockOf` and `collect`; there is no hardware, clock or I/O.
- [ ] The coin box can be tested alone: load counts, ask for an amount, check the coins or the refusal.
- [ ] Outcomes are named strings, so tests assert the exact failure reason.

## Reference design

```text
VendingMachine (facade, owns State)
 ├── state: MAINTENANCE | IDLE | HAS_CREDIT
 ├── CoinBox: counts per denomination; payOut(amount) -> coins or none
 ├── slots: slot -> Slot(price, count)
 ├── credit
 └── tray: coins waiting for the customer
```

Each public method begins with its state guard: `stock` and `loadCoins` need `MAINTENANCE`; `insert` rejects coins in `MAINTENANCE` into the tray; `service(true)` is allowed only from `IDLE`, so a customer's credit can never be stranded in service mode. `select` runs its checks in the order the statement lists, and asks the `CoinBox` to pay out `credit - price` only after every other check passed. `payOut` plans first: it fills a table of the fewest coins needed for every amount using each suffix of the denominations (largest first), then reconstructs the change by taking, for each denomination from the largest, the largest count that still allows an optimal finish. Only then does it remove the coins. A sale and a refund both end in `finish`, which moves the change to the tray, zeroes the credit and returns to `IDLE`.

Trade-offs: the textbook State pattern (one class per state, each implementing every event) shines when states have very different behavior or many events; with three states and simple guards, an enum is shorter and just as explicit. The dynamic program costs O(denominations x amount x coins) per sale, which is tiny at vending-machine scale and, unlike greedy, never refuses a sale it could make. Refunds use the same fewest-coins rule, so a customer may get a quarter back for five nickels; returning the inserted coins instead is a policy choice that would keep the inserted coins in an escrow until the sale.

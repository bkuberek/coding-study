# Vending Machine

## Statement

Design the controller of a coin-operated vending machine. It sells items from named slots, accepts a fixed set of coin values, keeps the coins it receives to give change later, and must never sell an item when it cannot return the exact change. An operator restocks it in a service mode. The machine's behavior depends on what state it is in, and that state must be explicit.

Implement the facade class `VendingMachine`.

## Input

- `VendingMachine(denominations)`: a machine accepting the coin values in `denominations`, in state `"MAINTENANCE"`, with no items and no coins.
- `service(enabled)`: `true` enters service mode, `false` leaves it.
- `stock(slot, price, count)`: adds `count` items to `slot` and sets the slot's price.
- `loadCoins(coin, count)`: adds coins for change.
- `insert(coin)`: a customer inserts a coin.
- `select(slot)`: a customer asks for an item.
- `refund()`: a customer asks for the credit back.
- `collect()`: the customer takes everything in the return tray.
- `state()`: the current state.
- `stockOf(slot)`: items left in a slot.

States and rules:

| State | Meaning | Transitions |
|-------|---------|-------------|
| `MAINTENANCE` | Service mode: `stock` and `loadCoins` work; customers cannot buy | `service(false)` goes to `IDLE` |
| `IDLE` | In service, no credit | `insert` of an accepted coin goes to `HAS_CREDIT`; `service(true)` goes to `MAINTENANCE` |
| `HAS_CREDIT` | In service, a customer has credit | a sale or a `refund` goes back to `IDLE` |

- An accepted coin goes into the machine's coin box and raises the credit; it can be given out as change later. A coin that is not accepted, or any coin inserted in `MAINTENANCE`, falls into the return tray.
- `select` checks, in order: the machine is in service, the slot exists, the slot is not empty, the credit covers the price, and the coin box can pay the change (`credit - price`) exactly. On success one item is sold, the change goes to the return tray, and the credit is 0. On failure nothing changes.
- Change and refunds are paid from the coin box with the fewest coins possible. Among equally few coins, the machine pays as many of the largest coin as it can, then of the next largest, and so on.

## Output

- `service` returns `true` when the transition happened, `false` otherwise (already in that mode, or `true` while a customer has credit).
- `stock` and `loadCoins` return `false` outside `MAINTENANCE`; `loadCoins` also for a coin that is not accepted.
- `insert` returns the credit after the coin, or `-1` when the coin was rejected.
- `select` returns `"DISPENSED"`, or the first failed check: `"OUT_OF_SERVICE"`, `"UNKNOWN_SLOT"`, `"SOLD_OUT"`, `"INSUFFICIENT_CREDIT"` or `"NO_CHANGE"`.
- `refund` returns the amount refunded into the tray, or `0` without credit.
- `collect` returns the coins in the tray from largest to smallest and empties it.
- `state` returns `"MAINTENANCE"`, `"IDLE"` or `"HAS_CREDIT"`.
- `stockOf` returns the number of items, or `-1` for a slot that was never stocked.

## Examples

### Example 1

<!-- case: ex1 -->

In service mode the operator stocks two items at 65 and loads 5- and 10-cent coins, then opens the machine. A 1-dollar coin gives a credit of 100 and change of 35, paid as three 10s and a 5 because there are no 25s in the box.

### Example 2

<!-- case: ex2 -->

The item costs 75, but the box holds only the inserted 100 and no 25s, so the sale fails with `NO_CHANGE` and the credit stays. A 3-cent coin is not accepted and drops into the tray. The refund returns the 100.

## Constraints

- 1 to 6 distinct denominations, each from 1 to 200.
- `1 <= price <= 500`, `0 <= count <= 50`; the credit never exceeds 1000.
- At most 50 coins of each value are loaded or inserted in a test.
- At most 200 calls per test. Slots are 1 to 4 letters or digits.

## Follow-ups

- How would you add card payments that need no change at all?
- What should happen to the credit when the machine loses power in the middle of a sale?

## Hints

### Hint 1

Make the state an enum and check it at the start of every method. Most operations are legal in only one or two states.

### Hint 2

Taking the largest coin first fails with limited coins: with 3s and 4s, change of 6 must be 3 + 3. Build a table of the fewest coins for every amount using the smaller denominations, then pick coins from the largest down.

### Hint 3

Plan the change before touching anything; when no plan exists, return `NO_CHANGE` without changing the inventory, the coins or the credit.

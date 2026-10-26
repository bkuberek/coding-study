# Parking Lot: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| strategy-allocator | optimal | O(log s) per park and leave; O(1) per lookup | O(s + v) | default answer; each rule lives in exactly one class |

Here `s` is the number of spots and `v` the number of tickets kept.

## Approach: strategy-allocator (Spot allocator with pricing strategies)

### Intuition

The statement hides three independent decisions behind one API: which spots a vehicle fits, which free spot it gets, and what its stay costs. Giving each decision its own home keeps the facade trivial and makes the announced change, a new pricing scheme, a one-class addition. The fit rule is data (a vehicle type lists the sizes it fits, smallest first), the allocation rule is a data structure (one priority queue of free spots per size), and the pricing rule is a strategy object.

### Algorithm

1. Build the allocator from the layout: create a `Spot(level, index)` for every character and put it into the free queue of its size, ordered by level, then index.
2. `park(t, plate, type)`: parse the type (unknown: `""`); reject a plate that has an open ticket. Ask the allocator for a spot: for each size the type fits, smallest first, pop the head of that size's queue if it is not empty. No spot: `""`. Otherwise issue ticket `T<n>`, remembering plate, type, spot and `t`, and index it by id and by plate.
3. `leave(t, id)`: remove the ticket (unknown or used: `-1`), drop the plate's entry, push the spot back into its size's queue, and return `pricing.fee(type, parkedAt, t)`.
4. `locate` reads the plate index; `freeSpots` sums the queue sizes of the sizes the type fits.
5. Pricing: `billableHours = max(1, ceil(duration / 3600))`. Hourly: `hours * rate`. Daily cap: `(hours / 24) * cap + min((hours % 24) * rate, cap)` with `cap = 8 * rate`.
6. `setPricing(name)`: look the name up in a registry of policy factories; replace the current policy, or return `false`.

### Correctness

Invariant: every spot is in exactly one place, either in the free queue of its size or on exactly one open ticket. Construction puts every spot in its queue; `park` moves one spot from a queue to a new ticket; `leave` moves it back. So no spot is ever handed out twice, and `freeSpots` counts exactly the free spots a type fits.

Allocation follows the rule: sizes are tried in the order the type lists them, smallest first, and only the first size with a free spot is used. Within a size, the queue's head is the free spot with the smallest `(level, index)`. The plate index holds exactly the plates with open tickets, so a parked plate is rejected and `locate` answers from it. The fee uses the policy object in place when `leave` runs, as the statement requires.

### Complexity

- Time: O(log s) per park and leave; O(1) per lookup — a heap pop or push per park and leave (TypeScript's sorted arrays make it O(s) in the worst case); `locate`, `setPricing` and `freeSpots` are map lookups over a constant number of sizes.
- Space: O(s + v) — every spot once, plus every ticket issued and not yet used.

### Trade-offs

- Scanning all spots on every `park` (as a first version would) is O(s) and still fine for a few hundred spots; the per-size queues matter once lots are large or the interviewer asks about allocation cost.
- A `Vehicle` class hierarchy (`Car extends Vehicle`) is a common answer, but vehicles here have no behavior, only data. An enum with a fit list and a rate keeps adding a type to one line. Prefer the hierarchy only if types gain behavior, such as vans needing two adjacent spots.
- The pricing registry maps names to factories, so configuration (a string) never leaks into the lot's logic. Passing the policy into the constructor would be the dependency-injection version of the same seam.

### Pitfalls and edge cases

- The smallest fitting size beats a lower level: a motorcycle takes a small spot on level 2 before a large spot on level 0.
- A zero-length stay still pays one hour; exactly 3600 seconds is one hour, 3601 is two.
- Using a ticket twice must fail, and the plate must be parkable again after leaving.
- The daily cap applies to the remainder as well: 23 hours cost 8 hours, not 23.
- An unknown vehicle type is `""` for `park` but `-1` for `freeSpots`.

### Language notes

- Python: an `Enum` whose members carry a tuple of fitting sizes and a rate (`__init__` on the enum unpacks them); `heapq` over `Spot` dataclasses with `order=True`; `typing.Protocol` for the pricing interface. `-(-a // b)` is integer ceiling division.
- TypeScript: string-literal types for sizes and a `Map` of vehicle definitions stand in for enums, which are not erasable syntax. There is no heap, so free spots stay in sorted arrays: `shift()` takes the best spot and a binary search reinserts a freed one.
- Java: enums with constructor fields, a `record Spot` implementing `Comparable`, `PriorityQueue` per size in an `EnumMap`, and `Map<String, Supplier<PricingPolicy>>` as the registry. `Math.ceilDiv` (Java 18 and later) rounds the hours up.
- Kotlin: `enum class` with properties, `fun interface PricingPolicy` so each policy is a lambda, `compareValuesBy` for the spot order and `firstNotNullOfOrNull` for "first size with a free spot".

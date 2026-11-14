# Parking Lot

## Statement

Design the software of a multi-level parking garage. Each level has a row of spots, and each spot is small, medium or large. Vehicles get the best spot that fits them, receive a ticket, and pay by the hour when they leave. The garage wants to try other pricing schemes later, so pricing must be easy to swap.

Implement the facade class `ParkingLot`. Time is passed in as `timestamp`, in seconds; nothing reads a clock.

## Input

- `ParkingLot(levels)`: `levels[i]` describes level `i`, one character per spot from index 0: `S` (small), `M` (medium) or `L` (large).
- `park(timestamp, plate, vehicleType)`: a vehicle arrives. `vehicleType` is `"MOTORCYCLE"`, `"CAR"` or `"VAN"`.
- `leave(timestamp, ticketId)`: the vehicle with this ticket leaves and pays.
- `locate(plate)`: where a vehicle is parked.
- `freeSpots(vehicleType)`: how many free spots a vehicle of this type would fit in.
- `setPricing(scheme)`: switches the pricing scheme to `"HOURLY"` or `"DAILY_CAP"`.

Fitting and allocation rules:

- A motorcycle fits any spot, a car fits medium and large spots, and a van fits only large spots.
- A vehicle gets a spot of the smallest size it fits that has a free spot; among those, the lowest level, then the lowest index.

Pricing (amounts in cents):

| Vehicle | Hourly rate |
|---------|-------------|
| `MOTORCYCLE` | 100 |
| `CAR` | 250 |
| `VAN` | 400 |

- `"HOURLY"` (the initial scheme): every started hour costs the hourly rate, with a minimum of one hour. A stay of 3600 seconds is one hour; 3601 seconds is two.
- `"DAILY_CAP"`: count started hours the same way, then split them into full days of 24 hours and a remainder. Each full day costs 8 times the hourly rate, and the remainder costs the hourly rate per hour but at most 8 times the hourly rate.
- The scheme in force when the vehicle leaves decides the fee.

## Output

- `park` returns a ticket id `"T<n>"`, where `n` counts the successful parks so far, starting at 1. It returns `""` when the vehicle type is unknown, the plate is already parked, or no fitting spot is free.
- `leave` returns the fee, or `-1` when the ticket is unknown or was already used. The spot becomes free.
- `locate` returns `"<level>-<index>"`, or `""` when the plate is not parked.
- `freeSpots` returns the count, or `-1` for an unknown vehicle type.
- `setPricing` returns `true`, or `false` for an unknown scheme, which leaves the current scheme in place.

## Examples

### Example 1

<!-- case: ex1 -->

The first car takes the medium spot on level 0, the motorcycle the small one and the van the large one. The second car takes the medium spot on level 1, and the third car, finding no free medium spot, takes the large spot there. The lot is now full, so the last motorcycle is turned away.

### Example 2

<!-- case: ex2 -->

The car stays exactly one hour and pays 250. The van stays one hour and one second, which is two started hours at 400. Its ticket cannot be used twice. Under the daily cap, a car that stays 25 hours pays one capped day, 2000, plus one hour, 250.

## Constraints

- `1 <= levels.length <= 10`, and each level has 1 to 100 spots.
- At most 1000 calls per test.
- `0 <= timestamp <= 10^9`; a vehicle never leaves before it parked.
- Plates are 1 to 10 letters or digits.

## Follow-ups

- How would you add electric-vehicle spots with chargers that only some cars may use?
- How would pricing work if the rate depended on the level, or on the time of day?

## Hints

### Hint 1

Separate the three decisions: which spot fits (vehicle type and spot size), which free spot to hand out (an allocator), and what a stay costs (a pricing policy).

### Hint 2

Keep the free spots of each size in a priority queue ordered by level and index; allocation tries the sizes a vehicle fits, smallest first.

### Hint 3

Make pricing an interface with one method, `fee(vehicle, parkedAt, leftAt)`. Each scheme is one small class, and `setPricing` only swaps the object.

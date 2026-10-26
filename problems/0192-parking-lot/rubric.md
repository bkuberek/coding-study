# Parking Lot: Rubric

## Responsibilities

- [ ] `ParkingLot` is a thin facade: it parses the request, issues tickets and delegates every decision to a collaborator.
- [ ] One allocator owns the free spots and alone decides which spot a vehicle gets; callers never compute levels or indexes.
- [ ] A pricing object alone computes fees; `leave` does not contain rate tables or rounding rules.
- [ ] The vehicle type knows which spot sizes it fits and its hourly rate, so no `if type == "CAR"` chains are spread through the code.
- [ ] A ticket records everything the fee needs (vehicle type, spot, arrival time), so leaving needs no other lookup.

## Extension points

- [ ] A new pricing scheme is one new class plus one registry entry; `ParkingLot`, tickets and the allocator do not change.
- [ ] A new vehicle type or spot size (for example electric-vehicle spots) changes the type and size definitions only.
- [ ] The allocation order (smallest fitting size, then level, then index) lives in one place and could be replaced by another policy, such as nearest to the exit.

## Patterns

- [ ] Pricing is a Strategy: an interface with one `fee` method and interchangeable implementations chosen at run time.
- [ ] Vehicle types and spot sizes are enums carrying data (fits, rates) instead of strings compared everywhere.
- [ ] Spots and tickets are immutable value objects; only the allocator's free lists and the facade's ticket maps change.

## Testability

- [ ] Time is a parameter of `park` and `leave`; no class reads a clock, so durations and boundaries are exact in tests.
- [ ] Each pricing policy can be tested alone with a vehicle type and two timestamps, without building a lot.
- [ ] The allocator can be tested alone from a layout, without tickets or pricing.
- [ ] Failures are sentinel return values (`""`, `-1`, `false`), so tests assert values rather than catch exceptions.

## Reference design

```text
ParkingLot (facade)
 ├── SpotAllocator ── free spots per SpotSize, each a min-heap of Spot(level, index)
 ├── PricingPolicy ◁── HourlyPricing, DailyCapPricing
 ├── tickets: id -> Ticket(id, plate, VehicleType, Spot, parkedAt)
 └── parked:  plate -> open Ticket
VehicleType: MOTORCYCLE, CAR, VAN with fits (sizes, smallest first) and hourlyRate
```

`ParkingLot` turns the vehicle type string into a `VehicleType`, rejects plates that are already parked, and asks the `SpotAllocator` for a spot. The allocator tries the sizes the type fits, smallest first, and pops the lowest `(level, index)` from that size's heap; releasing a spot pushes it back, so allocation and release are O(log s). A `Ticket` is created with the arrival time and stored twice, by id for `leave` and by plate for `locate`.

`leave` removes the ticket, frees the spot and asks the current `PricingPolicy` for the fee. Both policies share the "started hours, at least one" rule through one helper; `DailyCapPricing` then caps each day at 8 hours. `setPricing` looks the scheme up in a registry and replaces the policy object, which is the whole extension point.

Trade-offs: the fit table on `VehicleType` is simpler than a class hierarchy of vehicles, which would only add value if vehicles had behavior of their own. Heaps per size beat scanning every spot (O(s) per park) once lots have hundreds of spots, at the cost of a little more code. Pricing at leave time with the current scheme is a product decision; pricing at arrival time would store the policy on the ticket instead.

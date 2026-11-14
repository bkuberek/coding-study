# Parking Lot: Rubric

## Responsibilities

- [ ] `ParkingLot` alone decides which spot a car gets; callers never compute spot numbers.
- [ ] One structure answers "where is this plate parked?" without scanning every spot.

## Extension points

- [ ] Spot sizes (compact, large, accessible) can be added without changing callers of `park`.
- [ ] The allocation policy, lowest free spot first, lives in one place.

## Patterns

- [ ] Choosing a spot is a natural strategy seam, even while only one policy exists.

## Testability

- [ ] All behavior is observable through the public API: no clock, randomness or I/O.

## Reference design

`ParkingLot` keeps an occupancy array indexed by spot number and a map from plate to spot. `park` rejects a plate already in the map, then takes the first free spot in the array; `leave` removes the plate from the map and frees its spot; `available` is the number of spots minus the number of parked cars. Spot sizes would turn the array into one free list per size, behind a policy object that picks a list for a car.

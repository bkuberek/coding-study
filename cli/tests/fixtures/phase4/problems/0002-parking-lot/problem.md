# Parking Lot

## Statement

Model a parking lot with numbered spots. A car parks in the lowest-numbered free spot and frees it when it leaves.

## Input

- `ParkingLot(spots)`: a lot with spots numbered `0` to `spots - 1`, all free.
- `park(plate)`: parks the car with this plate.
- `leave(plate)`: the car with this plate leaves.
- `available()`: how many spots are free.

## Output

- `park` returns the spot number, or `-1` when the lot is full or the car is already parked.
- `leave` returns `true` when the car was parked, `false` otherwise.
- `available` returns the number of free spots.

## Examples

### Example 1

<!-- case: ex1 -->

The third car finds the lot full; once `A1` leaves, `C3` takes spot 0.

### Example 2

<!-- case: ex2 -->

A parked car cannot park twice, and a car that never parked cannot leave.

## Constraints

- `1 <= spots <= 1000`
- At most 1000 operations per case; plates are non-empty strings of letters and digits.

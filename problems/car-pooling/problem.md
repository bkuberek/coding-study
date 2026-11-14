# Car Pooling

## Statement

A shuttle drives along a straight road in one direction only, past locations numbered by their distance from the depot. It has `capacity` seats. You get the list of bookings for one run: `trips[i] = [passengers, start, end]` means that `passengers` people get on at location `start` and get off at location `end`.

Decide whether the shuttle can serve every booking without ever carrying more than `capacity` people. Riders who get off at a location leave before anyone gets on there, so a trip ending at location 5 and another starting at location 5 never share the shuttle.

Reference: this is our own wording of LeetCode problem 1094, [Car Pooling](https://leetcode.com/problems/car-pooling/).

## Input

- `trips`: the bookings, each `[passengers, start, end]`, in no particular order
- `capacity`: the number of seats

## Output

`true` if the number of people on board never exceeds `capacity`, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Between locations 3 and 4, the riders of all three bookings are on board: 2 + 3 + 1 = 6 people, more than the 5 seats.

### Example 2

<!-- case: ex2 -->

At location 5 the four riders of the first booking get off before the four riders of the second booking get on. With the two riders of the third booking, the load is 6 on both sides of location 5 and never more, so 6 seats are enough.

## Constraints

- `1 <= trips.length <= 10^4`
- `trips[i].length == 3`
- `1 <= passengers <= 100`
- `0 <= start < end <= 10^5`
- `1 <= capacity <= 10^6`

## Follow-ups

- Checking the load at every pickup is O(n^2). Can sorting help?
- Locations are small integers. Can you avoid sorting altogether?
- How would you report the first location where the shuttle overflows?

## Hints

### Hint 1

The load only changes at pickup and drop-off points, and it is highest right after some pickup.

### Hint 2

Turn each booking into two events: `+passengers` at `start` and `-passengers` at `end`. Processed in location order, with drop-offs first on ties, their running sum is the load.

### Hint 3

Since locations are bounded, add the events into an array indexed by location (a difference array) and take its prefix sums.

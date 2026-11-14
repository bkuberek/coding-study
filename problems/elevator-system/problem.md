# Elevator System

## Statement

Design the controller of a bank of elevators. People on a floor press a call button, a dispatcher assigns the call to one car, and people inside a car press the buttons of the floors they want. Each car follows a simple, predictable direction rule, and the building wants to experiment with different dispatch strategies.

Implement the facade class `ElevatorSystem`. Time advances only through `step`, one floor per tick; nothing reads a clock.

## Input

- `ElevatorSystem(cars, floors)`: cars are numbered from 0 and floors from 0 to `floors - 1`. Every car starts at floor 0, idle, with no stops.
- `call(floor, direction)`: a person on `floor` presses `"UP"` or `"DOWN"`. The dispatch strategy picks a car, and `floor` becomes one of its stops.
- `select(car, floor)`: a person inside `car` presses the button of `floor`, which becomes one of its stops.
- `step(ticks)`: advances time by `ticks` ticks.
- `status(car)`: where the car is and where it is going.
- `stops(car)`: the car's pending stops.
- `setStrategy(name)`: switches the dispatch strategy to `"NEAREST"` or `"ROUND_ROBIN"`.

Car rules:

- A car's direction is `UP`, `DOWN` or `IDLE`. A stop added while the car is idle at that very floor is served at once and not added. A car stops at every floor in its stops, whatever direction the call was for.
- In each tick the cars act one after the other, in car order. A car without stops is idle and does not move. An idle car with stops first picks a direction: towards its nearest stop, or `UP` when the nearest stops above and below are equally far.
- The car then moves one floor in its direction, and removes that floor from its stops if it is one. If no stops remain it becomes idle; if stops remain but none lies further in its direction, it reverses.

Dispatch strategies:

- `"NEAREST"` (the initial strategy): the car with the lowest cost, and among equal costs the lowest car number. An idle car's cost is its distance to `floor`. A moving car's cost is its distance to `floor` when `floor` lies strictly ahead of it; otherwise it is the distance to its furthest stop in its direction plus the distance from there back to `floor`.
- `"ROUND_ROBIN"`: cars 0, 1, 2, ... in turn, wrapping around; only accepted calls take a turn. A new strategy starts from its own initial state.

## Output

- `call` returns the number of the assigned car, or `-1` when `floor` does not exist, `direction` is neither `"UP"` nor `"DOWN"`, or the direction leads out of the building (`"UP"` on the top floor, `"DOWN"` on floor 0).
- `select` returns `true`, or `false` when the car or the floor does not exist.
- `status` returns `"<floor>:<direction>"`, for example `"3:UP"`, or `""` when the car does not exist.
- `stops` returns the pending stops in ascending order, or an empty list when the car does not exist.
- `setStrategy` returns `true`, or `false` for an unknown name, which keeps the current strategy.

## Examples

### Example 1

<!-- case: ex1 -->

Both cars are idle at floor 0, so the call to floor 5 costs 5 for each and goes to car 0. After one tick both cars move up. Car 1 reaches floor 3 after three ticks and becomes idle; car 0 reaches floor 5 after five. The call at floor 4 costs 1 for both idle cars, so car 0 wins the tie.

### Example 2

<!-- case: ex2 -->

On its way up to 6, the car gets a stop at 4 ahead of it and one at 1 behind it. It stops at 4 and keeps going up, because 6 is still ahead. At 6 nothing is left above, so it reverses and goes down to 1, where it becomes idle.

## Constraints

- `1 <= cars <= 8` and `2 <= floors <= 100`.
- `0 <= ticks <= 1000`.
- At most 1000 calls per test.

## Follow-ups

- How would cars honor the direction of a hall call, stopping for a `"DOWN"` call only while going down?
- How would you add a strategy that sends calls from the top floors to an express car?

## Hints

### Hint 1

Give each car its own object with a floor, a direction and a set of stops, and put the direction rule in its `tick` method. The facade only loops over cars.

### Hint 2

"Is there a stop ahead?" is the only question the direction rule needs: compare each stop with the current floor, signed by the direction.

### Hint 3

Make dispatch an interface with one method, `choose(cars, floor)`. The nearest-car cost is a method of the car, because only the car knows where it will turn.

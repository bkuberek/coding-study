# Elevator System: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| look-dispatch | optimal | O(c s) per call; O(c s) per tick | O(c s) | default answer; movement and dispatch are separate, swappable pieces |

Here `c` is the number of cars and `s` the number of pending stops of one car (at most the number of floors).

## Approach: look-dispatch (LOOK cars with a pluggable dispatch strategy)

### Intuition

An elevator controller has two questions that change for different reasons. "How does one car move?" is physics plus a fairness rule, and it belongs to the car. "Which car answers a hall call?" is policy, and buildings tune it, so it belongs behind an interface. The movement rule here is LOOK: keep going in your direction while there is work ahead, then turn. That rule is a three-state machine (`IDLE`, `UP`, `DOWN`) whose only input is "is there a stop ahead?". The nearest-car policy then needs one number from each car, how far it will travel to reach a floor, and that number follows directly from LOOK.

### Algorithm

1. `Car.addStop(f)`: when the car is idle at `f`, do nothing (the doors open at once); otherwise add `f` to the stop set.
2. `Car.tick()`:
   1. No stops: become idle and stay.
   2. Idle with stops: take the direction of the nearest stop; equal distances go up.
   3. Move one floor and remove that floor from the stops.
   4. No stops left: idle. Otherwise, if no stop lies strictly ahead in the direction, reverse.
3. `Car.travelTo(f)`: idle, or `f` strictly ahead: `|f - floor|`. Otherwise the car first reaches its furthest stop in its direction (`max` going up, `min` going down) and comes back: `|turn - floor| + |turn - f|`.
4. `NearestCar.choose`: the car with the smallest `travelTo(f)`, lowest index on ties. `RoundRobin.choose`: a counter modulo the number of cars.
5. Facade: `call` validates the floor and direction, asks the strategy, adds the stop; `select` validates and adds the stop; `step` ticks every car in order, `ticks` times; `setStrategy` swaps the strategy object through a registry of factories.

### Correctness

Invariant: after every tick, a car is idle exactly when it has no stops, and a moving car has at least one stop strictly ahead in its direction. Step 2.4 establishes it at the end of each tick: either the stops are empty (idle), or a stop is ahead (keep going), or every stop is behind or at the current floor, and reversing puts a stop ahead because the current floor was just removed. Adding stops between ticks never breaks it, since it only adds work. So a moving car never moves past the building's ends: there is always a stop ahead, inside the building, before it would.

Every stop is eventually served: a moving car reaches its furthest stop ahead within `floors` ticks, serving everything on the way, then reverses and does the same in the other direction. `travelTo` counts exactly the floors that path visits before `f`, so `NearestCar` picks the car that arrives first under LOOK, ties going to the lowest index as specified.

### Complexity

- Time: O(c s) per call; O(c s) per tick — the nearest-car strategy asks each car for its cost, which needs its furthest stop (O(1) with a sorted set, O(s) with a hash set); a tick checks "stop ahead" per car, again O(1) or O(s).
- Space: O(c s) — every car's stop set.

### Trade-offs

- Tracking direction per hall call (stop for a `"DOWN"` call only while going down, or at the turning point) is how real controllers avoid picking up passengers going the wrong way. It needs stops tagged with a direction and a richer stop test, so the reference keeps a plain set and leaves it as the main follow-up.
- SCAN (always run to the end of the shaft) is simpler to reason about but wastes travel; LOOK turns at the last stop. Nearest-car with LOOK costs is a classic, cheap heuristic; real systems also weigh load and waiting time, which is exactly what a new strategy class would do.
- The simulation is discrete and single-threaded. A real controller is event-driven with door timers; the tick model trades realism for determinism, which is what makes it testable.

### Pitfalls and edge cases

- A call at an idle car's own floor must not create a stop, or the car would wait for a tick that never moves it.
- A stop at the current floor of a moving car is served on the way back, not immediately.
- After serving a floor, recheck the direction: reverse when nothing is ahead, go idle when nothing is left.
- `"UP"` on the top floor and `"DOWN"` on floor 0 are invalid; so is any other direction string.
- Round robin takes a turn only for accepted calls, and a newly selected strategy starts fresh.
- The nearest-car cost of a moving car for a floor behind it goes through the turning point; using plain distance would send calls to a car moving away.

### Language notes

- Python: `Direction` is an `Enum` whose values are the signed steps, so `floor += direction.value`; `min(stops, key=(distance, -stop))` breaks the nearest-stop tie upwards. `typing.Protocol` describes the strategy.
- TypeScript: a string-literal union for the direction plus a `Record` of steps replaces an enum; a `Set<number>` holds stops, so `Math.max(...stops)` finds the turning point.
- Java: an enum with a `step` field and `reversed()`, a `TreeSet<Integer>` per car so `higher`, `lower`, `first` and `last` answer "ahead" and "turning point" in O(log s), and a `Map` of `Supplier`s as the strategy registry. `switch` expressions validate the direction.
- Kotlin: the same `TreeSet`, an `enum class` with a property, `when` for the state transitions and `?: return` for the nearest-stop choice. `minBy` returns the first minimal index, which is the required tie-break.

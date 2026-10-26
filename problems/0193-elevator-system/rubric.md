# Elevator System: Rubric

## Responsibilities

- [ ] Each `Car` owns its floor, direction and stops, and alone applies the direction rule in its own `tick`.
- [ ] A dispatch strategy alone decides which car serves a hall call; the facade never compares cars itself.
- [ ] The car computes its own travel cost to a floor, so strategies use it without knowing how a car turns.
- [ ] `ElevatorSystem` validates input (floors, cars, directions) and delegates; it holds no movement logic.

## Extension points

- [ ] A new dispatch strategy (zoned, express, least busy) is one new class plus a registry entry; cars and the facade do not change.
- [ ] A different movement rule (for example honoring hall call directions) changes `Car` only.
- [ ] The number of cars and floors is configuration, not code.

## Patterns

- [ ] Dispatch is a Strategy with one method, `choose(cars, floor)`, selected by name at run time.
- [ ] The car is an explicit state machine: `IDLE`, `UP` and `DOWN`, with each transition in one place (pick a direction when idle, reverse when nothing is ahead, idle when empty).
- [ ] Direction is an enum with a signed step (`+1`, `-1`, `0`), so "ahead" is one multiplication instead of branches.

## Testability

- [ ] Time advances only through `step`; there are no threads, timers or sleeps, so every scenario replays exactly.
- [ ] A car can be tested alone: add stops, tick, and check floor and direction.
- [ ] A strategy can be tested alone with a list of cars in known states.
- [ ] All state is observable through `status` and `stops`; tests never need internal access.

## Reference design

```text
ElevatorSystem (facade: validation, ticking, strategy registry)
 ├── cars: Car[]       Car(floor, direction, stops)  tick(), addStop(), travelTo(floor)
 └── strategy: DispatchStrategy ◁── NearestCar, RoundRobin
Direction: UP(+1), DOWN(-1), IDLE(0)
```

`ElevatorSystem` checks that a call's floor exists and that its direction stays inside the building, then asks the current `DispatchStrategy` for a car and adds the floor to that car's stops. `select` validates and adds directly. `step` ticks every car in order, `ticks` times.

`Car.tick` is the whole state machine: with no stops it is `IDLE`; when idle with stops it picks the direction of the nearest stop (ties up); it moves one floor, serves that floor if it is a stop, and then either becomes idle, keeps going while a stop lies ahead, or reverses. This is the LOOK rule: a car never turns while it still has work in its direction, which bounds waiting time and avoids zig-zagging. `Car.travelTo(floor)` mirrors the same rule: straight there if ahead or idle, otherwise via the furthest stop in the current direction.

`NearestCar` takes the minimum of `(travelTo(floor), carIndex)`; `RoundRobin` keeps a counter. Each is a few lines, and adding a third is the point of the seam. Trade-off: stops are a plain set of floors, so a car going up also stops for people who want to go down. Tracking the call direction per stop would fix that at the price of a more complex stop model, which is the first follow-up an interviewer is likely to ask.

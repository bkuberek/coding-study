from enum import Enum
from typing import Protocol


class Direction(Enum):
    UP = 1
    DOWN = -1
    IDLE = 0


class Car:
    """One elevator car: a floor, a direction and a set of stops, moved by the LOOK rule."""

    def __init__(self) -> None:
        self.floor = 0
        self.direction = Direction.IDLE
        self.stops: set[int] = set()

    def add_stop(self, floor: int) -> None:
        if self.direction is Direction.IDLE and floor == self.floor:
            return  # already there: the doors open at once
        self.stops.add(floor)

    def tick(self) -> None:
        if not self.stops:
            self.direction = Direction.IDLE
            return
        if self.direction is Direction.IDLE:
            nearest = min(self.stops, key=lambda stop: (abs(stop - self.floor), -stop))
            self.direction = Direction.UP if nearest > self.floor else Direction.DOWN
        self.floor += self.direction.value
        self.stops.discard(self.floor)
        if not self.stops:
            self.direction = Direction.IDLE
        elif not self.has_stop_ahead():
            self.direction = Direction.DOWN if self.direction is Direction.UP else Direction.UP

    def has_stop_ahead(self) -> bool:
        return any((stop - self.floor) * self.direction.value > 0 for stop in self.stops)

    def travel_to(self, floor: int) -> int:
        """Floors the car travels before reaching `floor` under the LOOK rule."""
        if self.direction is Direction.IDLE or (floor - self.floor) * self.direction.value > 0:
            return abs(floor - self.floor)
        turn = max(self.stops) if self.direction is Direction.UP else min(self.stops)
        return abs(turn - self.floor) + abs(turn - floor)

    def status(self) -> str:
        return f"{self.floor}:{self.direction.name}"


class DispatchStrategy(Protocol):
    def choose(self, cars: list[Car], floor: int) -> int: ...


class NearestCar:
    def choose(self, cars: list[Car], floor: int) -> int:
        return min(range(len(cars)), key=lambda index: (cars[index].travel_to(floor), index))


class RoundRobin:
    def __init__(self) -> None:
        self._next = 0

    def choose(self, cars: list[Car], floor: int) -> int:
        chosen = self._next
        self._next = (self._next + 1) % len(cars)
        return chosen


STRATEGIES: dict[str, type[DispatchStrategy]] = {"NEAREST": NearestCar, "ROUND_ROBIN": RoundRobin}


class ElevatorSystem:
    def __init__(self, cars: int, floors: int) -> None:
        self._cars = [Car() for _ in range(cars)]
        self._floors = floors
        self._strategy: DispatchStrategy = NearestCar()

    def call(self, floor: int, direction: str) -> int:
        if not self._valid_floor(floor) or not self._can_travel(floor, direction):
            return -1
        chosen = self._strategy.choose(self._cars, floor)
        self._cars[chosen].add_stop(floor)
        return chosen

    def select(self, car: int, floor: int) -> bool:
        if not self._valid_car(car) or not self._valid_floor(floor):
            return False
        self._cars[car].add_stop(floor)
        return True

    def step(self, ticks: int) -> None:
        for _ in range(ticks):
            for car in self._cars:
                car.tick()

    def status(self, car: int) -> str:
        return self._cars[car].status() if self._valid_car(car) else ""

    def stops(self, car: int) -> list[int]:
        return sorted(self._cars[car].stops) if self._valid_car(car) else []

    def set_strategy(self, name: str) -> bool:
        strategy = STRATEGIES.get(name)
        if strategy is None:
            return False
        self._strategy = strategy()
        return True

    def _valid_car(self, car: int) -> bool:
        return 0 <= car < len(self._cars)

    def _valid_floor(self, floor: int) -> bool:
        return 0 <= floor < self._floors

    def _can_travel(self, floor: int, direction: str) -> bool:
        if direction == "UP":
            return floor < self._floors - 1
        if direction == "DOWN":
            return floor > 0
        return False

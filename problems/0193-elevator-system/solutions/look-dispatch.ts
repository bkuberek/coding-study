type Direction = "UP" | "DOWN" | "IDLE";

const STEP: Record<Direction, number> = { UP: 1, DOWN: -1, IDLE: 0 };

// One elevator car: a floor, a direction and a set of stops, moved by the LOOK rule.
class Car {
  floor = 0;
  direction: Direction = "IDLE";
  readonly stops = new Set<number>();

  addStop(floor: number): void {
    if (this.direction === "IDLE" && floor === this.floor) {
      return; // already there: the doors open at once
    }
    this.stops.add(floor);
  }

  tick(): void {
    if (this.stops.size === 0) {
      this.direction = "IDLE";
      return;
    }
    if (this.direction === "IDLE") {
      this.direction = this.towardsNearestStop();
    }
    this.floor += STEP[this.direction];
    this.stops.delete(this.floor);
    if (this.stops.size === 0) {
      this.direction = "IDLE";
    } else if (!this.hasStopAhead()) {
      this.direction = this.direction === "UP" ? "DOWN" : "UP";
    }
  }

  // Floors the car travels before reaching `floor` under the LOOK rule.
  travelTo(floor: number): number {
    if (this.direction === "IDLE" || (floor - this.floor) * STEP[this.direction] > 0) {
      return Math.abs(floor - this.floor);
    }
    const stops = [...this.stops];
    const turn = this.direction === "UP" ? Math.max(...stops) : Math.min(...stops);
    return Math.abs(turn - this.floor) + Math.abs(turn - floor);
  }

  status(): string {
    return `${this.floor}:${this.direction}`;
  }

  private hasStopAhead(): boolean {
    return [...this.stops].some((stop) => (stop - this.floor) * STEP[this.direction] > 0);
  }

  // Up or down towards the nearest stop; up when the nearest stops are equally far.
  private towardsNearestStop(): Direction {
    let best = Infinity;
    let direction: Direction = "UP";
    for (const stop of this.stops) {
      const distance = Math.abs(stop - this.floor);
      if (distance < best || (distance === best && stop > this.floor)) {
        best = distance;
        direction = stop > this.floor ? "UP" : "DOWN";
      }
    }
    return direction;
  }
}

interface DispatchStrategy {
  choose(cars: readonly Car[], floor: number): number;
}

class NearestCar implements DispatchStrategy {
  choose(cars: readonly Car[], floor: number): number {
    let chosen = 0;
    cars.forEach((car, index) => {
      if (car.travelTo(floor) < cars[chosen].travelTo(floor)) {
        chosen = index;
      }
    });
    return chosen;
  }
}

class RoundRobin implements DispatchStrategy {
  private next = 0;

  choose(cars: readonly Car[], floor: number): number {
    const chosen = this.next;
    this.next = (this.next + 1) % cars.length;
    return chosen;
  }
}

const STRATEGIES = new Map<string, () => DispatchStrategy>([
  ["NEAREST", () => new NearestCar()],
  ["ROUND_ROBIN", () => new RoundRobin()],
]);

export class ElevatorSystem {
  private readonly cars: Car[];
  private readonly floors: number;
  private strategy: DispatchStrategy = new NearestCar();

  constructor(cars: number, floors: number) {
    this.cars = Array.from({ length: cars }, () => new Car());
    this.floors = floors;
  }

  call(floor: number, direction: string): number {
    if (!this.validFloor(floor) || !this.canTravel(floor, direction)) {
      return -1;
    }
    const chosen = this.strategy.choose(this.cars, floor);
    this.cars[chosen].addStop(floor);
    return chosen;
  }

  select(car: number, floor: number): boolean {
    if (!this.validCar(car) || !this.validFloor(floor)) {
      return false;
    }
    this.cars[car].addStop(floor);
    return true;
  }

  step(ticks: number): void {
    for (let tick = 0; tick < ticks; tick++) {
      for (const car of this.cars) {
        car.tick();
      }
    }
  }

  status(car: number): string {
    return this.validCar(car) ? this.cars[car].status() : "";
  }

  stops(car: number): number[] {
    return this.validCar(car) ? [...this.cars[car].stops].sort((a, b) => a - b) : [];
  }

  setStrategy(name: string): boolean {
    const create = STRATEGIES.get(name);
    if (create === undefined) {
      return false;
    }
    this.strategy = create();
    return true;
  }

  private validCar(car: number): boolean {
    return car >= 0 && car < this.cars.length;
  }

  private validFloor(floor: number): boolean {
    return floor >= 0 && floor < this.floors;
  }

  private canTravel(floor: number, direction: string): boolean {
    if (direction === "UP") {
      return floor < this.floors - 1;
    }
    if (direction === "DOWN") {
      return floor > 0;
    }
    return false;
  }
}

use std::collections::HashSet;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Direction {
    Up,
    Down,
    Idle,
}

impl Direction {
    /// The signed floor step.
    fn step(self) -> i32 {
        match self {
            Direction::Up => 1,
            Direction::Down => -1,
            Direction::Idle => 0,
        }
    }

    fn name(self) -> &'static str {
        match self {
            Direction::Up => "UP",
            Direction::Down => "DOWN",
            Direction::Idle => "IDLE",
        }
    }
}

/// One elevator car: a floor, a direction and a set of stops, moved by the LOOK rule.
struct Car {
    floor: i32,
    direction: Direction,
    stops: HashSet<i32>,
}

impl Car {
    fn new() -> Self {
        Car {
            floor: 0,
            direction: Direction::Idle,
            stops: HashSet::new(),
        }
    }

    fn add_stop(&mut self, floor: i32) {
        if self.direction == Direction::Idle && floor == self.floor {
            return; // already there: the doors open at once
        }
        self.stops.insert(floor);
    }

    fn tick(&mut self) {
        if self.stops.is_empty() {
            self.direction = Direction::Idle;
            return;
        }
        if self.direction == Direction::Idle {
            self.direction = if self.nearest_stop() > self.floor {
                Direction::Up
            } else {
                Direction::Down
            };
        }
        self.floor += self.direction.step();
        self.stops.remove(&self.floor);
        if self.stops.is_empty() {
            self.direction = Direction::Idle;
        } else if !self.has_stop_ahead() {
            self.direction = if self.direction == Direction::Up {
                Direction::Down
            } else {
                Direction::Up
            };
        }
    }

    /// The closest stop, the higher one on a tie.
    fn nearest_stop(&self) -> i32 {
        let key = |stop: &i32| ((stop - self.floor).abs(), -stop);
        self.stops
            .iter()
            .copied()
            .min_by_key(key)
            .unwrap_or(self.floor)
    }

    fn has_stop_ahead(&self) -> bool {
        self.stops
            .iter()
            .any(|stop| (stop - self.floor) * self.direction.step() > 0)
    }

    /// The last stop the car reaches before it turns: the highest while going up, the lowest
    /// while going down.
    fn turning_point(&self) -> i32 {
        let stops = self.stops.iter().copied();
        let turn = if self.direction == Direction::Up {
            stops.max()
        } else {
            stops.min()
        };
        turn.unwrap_or(self.floor)
    }

    /// The floors the car travels before reaching `floor` under the LOOK rule.
    fn travel_to(&self, floor: i32) -> i32 {
        if self.direction == Direction::Idle || (floor - self.floor) * self.direction.step() > 0 {
            return (floor - self.floor).abs();
        }
        let turn = self.turning_point();
        (turn - self.floor).abs() + (turn - floor).abs()
    }

    fn status(&self) -> String {
        format!("{}:{}", self.floor, self.direction.name())
    }
}

trait DispatchStrategy {
    fn choose(&mut self, cars: &[Car], floor: i32) -> usize;
}

struct NearestCar;

impl DispatchStrategy for NearestCar {
    fn choose(&mut self, cars: &[Car], floor: i32) -> usize {
        // `min_by_key` returns the first minimum, which is the required tie-break on the index.
        (0..cars.len())
            .min_by_key(|&index| cars[index].travel_to(floor))
            .unwrap_or(0)
    }
}

struct RoundRobin {
    next: usize,
}

impl DispatchStrategy for RoundRobin {
    fn choose(&mut self, cars: &[Car], _floor: i32) -> usize {
        let chosen = self.next;
        self.next = (self.next + 1) % cars.len();
        chosen
    }
}

pub struct ElevatorSystem {
    cars: Vec<Car>,
    floors: i32,
    strategy: Box<dyn DispatchStrategy>,
}

impl ElevatorSystem {
    pub fn new(cars: i32, floors: i32) -> Self {
        ElevatorSystem {
            cars: (0..cars).map(|_| Car::new()).collect(),
            floors,
            strategy: Box::new(NearestCar),
        }
    }

    pub fn call(&mut self, floor: i32, direction: String) -> i32 {
        if !self.valid_floor(floor) || !self.can_travel(floor, &direction) {
            return -1;
        }
        let chosen = self.strategy.choose(&self.cars, floor);
        self.cars[chosen].add_stop(floor);
        chosen as i32
    }

    pub fn select(&mut self, car: i32, floor: i32) -> bool {
        if !self.valid_floor(floor) {
            return false;
        }
        match self.car_mut(car) {
            Some(car) => {
                car.add_stop(floor);
                true
            }
            None => false,
        }
    }

    pub fn step(&mut self, ticks: i32) {
        for _ in 0..ticks {
            for car in &mut self.cars {
                car.tick();
            }
        }
    }

    pub fn status(&mut self, car: i32) -> String {
        self.car_mut(car)
            .map_or_else(String::new, |car| car.status())
    }

    pub fn stops(&mut self, car: i32) -> Vec<i32> {
        let mut stops: Vec<i32> = self
            .car_mut(car)
            .map_or_else(Vec::new, |car| car.stops.iter().copied().collect());
        stops.sort_unstable();
        stops
    }

    pub fn set_strategy(&mut self, name: String) -> bool {
        self.strategy = match name.as_str() {
            "NEAREST" => Box::new(NearestCar),
            "ROUND_ROBIN" => Box::new(RoundRobin { next: 0 }),
            _ => return false,
        };
        true
    }

    fn car_mut(&mut self, car: i32) -> Option<&mut Car> {
        usize::try_from(car)
            .ok()
            .and_then(|index| self.cars.get_mut(index))
    }

    fn valid_floor(&self, floor: i32) -> bool {
        0 <= floor && floor < self.floors
    }

    fn can_travel(&self, floor: i32, direction: &str) -> bool {
        match direction {
            "UP" => floor < self.floors - 1,
            "DOWN" => floor > 0,
            _ => false,
        }
    }
}

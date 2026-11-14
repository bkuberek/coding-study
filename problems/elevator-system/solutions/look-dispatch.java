import java.util.*;
import java.util.function.Supplier;

public class ElevatorSystem {
    private enum Direction {
        UP(1), DOWN(-1), IDLE(0);

        final int step;

        Direction(int step) {
            this.step = step;
        }

        Direction reversed() {
            return this == UP ? DOWN : UP;
        }
    }

    /** One elevator car: a floor, a direction and a set of stops, moved by the LOOK rule. */
    private static final class Car {
        int floor;
        Direction direction = Direction.IDLE;
        final TreeSet<Integer> stops = new TreeSet<>();

        void addStop(int target) {
            if (direction == Direction.IDLE && target == floor) {
                return; // already there: the doors open at once
            }
            stops.add(target);
        }

        void tick() {
            if (stops.isEmpty()) {
                direction = Direction.IDLE;
                return;
            }
            if (direction == Direction.IDLE) {
                direction = towardsNearestStop();
            }
            floor += direction.step;
            stops.remove(floor);
            if (stops.isEmpty()) {
                direction = Direction.IDLE;
            } else if (!hasStopAhead()) {
                direction = direction.reversed();
            }
        }

        /** Floors the car travels before reaching {@code target} under the LOOK rule. */
        int travelTo(int target) {
            if (direction == Direction.IDLE || (target - floor) * direction.step > 0) {
                return Math.abs(target - floor);
            }
            int turn = direction == Direction.UP ? stops.last() : stops.first();
            return Math.abs(turn - floor) + Math.abs(turn - target);
        }

        String status() {
            return floor + ":" + direction.name();
        }

        private boolean hasStopAhead() {
            return direction == Direction.UP ? stops.higher(floor) != null : stops.lower(floor) != null;
        }

        /** Up or down towards the nearest stop; up when the nearest stops are equally far. */
        private Direction towardsNearestStop() {
            Integer above = stops.higher(floor);
            Integer below = stops.lower(floor);
            if (below == null) {
                return Direction.UP;
            }
            if (above == null) {
                return Direction.DOWN;
            }
            return above - floor <= floor - below ? Direction.UP : Direction.DOWN;
        }
    }

    private interface DispatchStrategy {
        int choose(List<Car> cars, int floor);
    }

    private static final class NearestCar implements DispatchStrategy {
        public int choose(List<Car> cars, int floor) {
            int chosen = 0;
            for (int index = 1; index < cars.size(); index++) {
                if (cars.get(index).travelTo(floor) < cars.get(chosen).travelTo(floor)) {
                    chosen = index;
                }
            }
            return chosen;
        }
    }

    private static final class RoundRobin implements DispatchStrategy {
        private int next;

        public int choose(List<Car> cars, int floor) {
            int chosen = next;
            next = (next + 1) % cars.size();
            return chosen;
        }
    }

    private static final Map<String, Supplier<DispatchStrategy>> STRATEGIES =
            Map.of("NEAREST", NearestCar::new, "ROUND_ROBIN", RoundRobin::new);

    private final List<Car> cars = new ArrayList<>();
    private final int floors;
    private DispatchStrategy strategy = new NearestCar();

    public ElevatorSystem(int cars, int floors) {
        for (int index = 0; index < cars; index++) {
            this.cars.add(new Car());
        }
        this.floors = floors;
    }

    public int call(int floor, String direction) {
        if (!validFloor(floor) || !canTravel(floor, direction)) {
            return -1;
        }
        int chosen = strategy.choose(cars, floor);
        cars.get(chosen).addStop(floor);
        return chosen;
    }

    public boolean select(int car, int floor) {
        if (!validCar(car) || !validFloor(floor)) {
            return false;
        }
        cars.get(car).addStop(floor);
        return true;
    }

    public void step(int ticks) {
        for (int tick = 0; tick < ticks; tick++) {
            cars.forEach(Car::tick);
        }
    }

    public String status(int car) {
        return validCar(car) ? cars.get(car).status() : "";
    }

    public List<Integer> stops(int car) {
        return validCar(car) ? List.copyOf(cars.get(car).stops) : List.of();
    }

    public boolean setStrategy(String name) {
        Supplier<DispatchStrategy> create = STRATEGIES.get(name);
        if (create == null) {
            return false;
        }
        strategy = create.get();
        return true;
    }

    private boolean validCar(int car) {
        return car >= 0 && car < cars.size();
    }

    private boolean validFloor(int floor) {
        return floor >= 0 && floor < floors;
    }

    private boolean canTravel(int floor, String direction) {
        return switch (direction) {
            case "UP" -> floor < floors - 1;
            case "DOWN" -> floor > 0;
            default -> false;
        };
    }
}

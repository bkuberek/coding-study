import java.util.TreeSet
import kotlin.math.abs

private enum class Direction(val step: Int) {
    UP(1), DOWN(-1), IDLE(0);

    fun reversed(): Direction = if (this == UP) DOWN else UP
}

/** One elevator car: a floor, a direction and a set of stops, moved by the LOOK rule. */
private class Car {
    var floor = 0
        private set
    var direction = Direction.IDLE
        private set
    val stops = TreeSet<Int>()

    fun addStop(target: Int) {
        if (direction == Direction.IDLE && target == floor) {
            return // already there: the doors open at once
        }
        stops += target
    }

    fun tick() {
        if (stops.isEmpty()) {
            direction = Direction.IDLE
            return
        }
        if (direction == Direction.IDLE) {
            direction = towardsNearestStop()
        }
        floor += direction.step
        stops -= floor
        direction = when {
            stops.isEmpty() -> Direction.IDLE
            hasStopAhead() -> direction
            else -> direction.reversed()
        }
    }

    /** Floors the car travels before reaching [target] under the LOOK rule. */
    fun travelTo(target: Int): Int {
        if (direction == Direction.IDLE || (target - floor) * direction.step > 0) {
            return abs(target - floor)
        }
        val turn = if (direction == Direction.UP) stops.last() else stops.first()
        return abs(turn - floor) + abs(turn - target)
    }

    fun status(): String = "$floor:${direction.name}"

    private fun hasStopAhead(): Boolean =
        if (direction == Direction.UP) stops.higher(floor) != null else stops.lower(floor) != null

    /** Up or down towards the nearest stop; up when the nearest stops are equally far. */
    private fun towardsNearestStop(): Direction {
        val above = stops.higher(floor) ?: return Direction.DOWN
        val below = stops.lower(floor) ?: return Direction.UP
        return if (above - floor <= floor - below) Direction.UP else Direction.DOWN
    }
}

private fun interface DispatchStrategy {
    fun choose(cars: List<Car>, floor: Int): Int
}

private class NearestCar : DispatchStrategy {
    override fun choose(cars: List<Car>, floor: Int): Int = cars.indices.minBy { cars[it].travelTo(floor) }
}

private class RoundRobin : DispatchStrategy {
    private var next = 0

    override fun choose(cars: List<Car>, floor: Int): Int = next.also { next = (next + 1) % cars.size }
}

private val strategies: Map<String, () -> DispatchStrategy> = mapOf("NEAREST" to ::NearestCar, "ROUND_ROBIN" to ::RoundRobin)

class ElevatorSystem(cars: Int, private val floors: Int) {
    private val cars = List(cars) { Car() }
    private var strategy: DispatchStrategy = NearestCar()

    fun call(floor: Int, direction: String): Int {
        if (!validFloor(floor) || !canTravel(floor, direction)) {
            return -1
        }
        val chosen = strategy.choose(cars, floor)
        cars[chosen].addStop(floor)
        return chosen
    }

    fun select(car: Int, floor: Int): Boolean {
        if (!validCar(car) || !validFloor(floor)) {
            return false
        }
        cars[car].addStop(floor)
        return true
    }

    fun step(ticks: Int) {
        repeat(ticks) { cars.forEach(Car::tick) }
    }

    fun status(car: Int): String = cars.getOrNull(car)?.status() ?: ""

    fun stops(car: Int): List<Int> = cars.getOrNull(car)?.stops?.toList() ?: emptyList()

    fun setStrategy(name: String): Boolean {
        strategy = strategies[name]?.invoke() ?: return false
        return true
    }

    private fun validCar(car: Int): Boolean = car in cars.indices

    private fun validFloor(floor: Int): Boolean = floor in 0 until floors

    private fun canTravel(floor: Int, direction: String): Boolean = when (direction) {
        "UP" -> floor < floors - 1
        "DOWN" -> floor > 0
        else -> false
    }
}

import java.util.EnumMap
import java.util.PriorityQueue

private const val SECONDS_PER_HOUR = 3600L
private const val HOURS_PER_DAY = 24L
private const val DAILY_CAP_HOURS = 8L

private enum class SpotSize(val code: Char) { SMALL('S'), MEDIUM('M'), LARGE('L') }

private enum class VehicleType(val fits: List<SpotSize>, val hourlyRate: Long) {
    MOTORCYCLE(listOf(SpotSize.SMALL, SpotSize.MEDIUM, SpotSize.LARGE), 100),
    CAR(listOf(SpotSize.MEDIUM, SpotSize.LARGE), 250),
    VAN(listOf(SpotSize.LARGE), 400),
}

private data class Spot(val level: Int, val index: Int, val size: SpotSize) : Comparable<Spot> {
    override fun compareTo(other: Spot): Int = compareValuesBy(this, other, Spot::level, Spot::index)

    val label: String get() = "$level-$index"
}

private data class Ticket(val id: String, val plate: String, val vehicle: VehicleType, val spot: Spot, val parkedAt: Long)

private fun interface PricingPolicy {
    fun fee(vehicle: VehicleType, parkedAt: Long, leftAt: Long): Long
}

/** Started hours, at least one. */
private fun billableHours(parkedAt: Long, leftAt: Long): Long =
    maxOf(1L, Math.ceilDiv(leftAt - parkedAt, SECONDS_PER_HOUR))

private val hourlyPricing = PricingPolicy { vehicle, parkedAt, leftAt ->
    billableHours(parkedAt, leftAt) * vehicle.hourlyRate
}

/** Hourly, but each started day costs at most DAILY_CAP_HOURS hours. */
private val dailyCapPricing = PricingPolicy { vehicle, parkedAt, leftAt ->
    val hours = billableHours(parkedAt, leftAt)
    val cap = DAILY_CAP_HOURS * vehicle.hourlyRate
    hours / HOURS_PER_DAY * cap + minOf(hours % HOURS_PER_DAY * vehicle.hourlyRate, cap)
}

private val pricingSchemes = mapOf("HOURLY" to hourlyPricing, "DAILY_CAP" to dailyCapPricing)

/** Free spots per size; hands out the smallest fitting size, then the lowest level and index. */
private class SpotAllocator(layout: List<String>) {
    private val free = EnumMap<SpotSize, PriorityQueue<Spot>>(SpotSize::class.java)

    init {
        SpotSize.entries.forEach { free[it] = PriorityQueue() }
        layout.forEachIndexed { level, row ->
            row.forEachIndexed { index, code ->
                val size = SpotSize.entries.first { it.code == code }
                free.getValue(size).add(Spot(level, index, size))
            }
        }
    }

    fun allocate(vehicle: VehicleType): Spot? = vehicle.fits.firstNotNullOfOrNull { free.getValue(it).poll() }

    fun release(spot: Spot) {
        free.getValue(spot.size).add(spot)
    }

    fun freeCount(vehicle: VehicleType): Int = vehicle.fits.sumOf { free.getValue(it).size }
}

class ParkingLot(levels: List<String>) {
    private val allocator = SpotAllocator(levels)
    private var pricing = hourlyPricing
    private val tickets = HashMap<String, Ticket>()
    private val parked = HashMap<String, Ticket>()
    private var issued = 0

    fun park(timestamp: Long, plate: String, vehicleType: String): String {
        val vehicle = vehicleOf(vehicleType) ?: return ""
        if (plate in parked) {
            return ""
        }
        val spot = allocator.allocate(vehicle) ?: return ""
        issued++
        val ticket = Ticket("T$issued", plate, vehicle, spot, timestamp)
        tickets[ticket.id] = ticket
        parked[plate] = ticket
        return ticket.id
    }

    fun leave(timestamp: Long, ticketId: String): Long {
        val ticket = tickets.remove(ticketId) ?: return -1
        parked.remove(ticket.plate)
        allocator.release(ticket.spot)
        return pricing.fee(ticket.vehicle, ticket.parkedAt, timestamp)
    }

    fun locate(plate: String): String = parked[plate]?.spot?.label ?: ""

    fun freeSpots(vehicleType: String): Int = vehicleOf(vehicleType)?.let(allocator::freeCount) ?: -1

    fun setPricing(scheme: String): Boolean {
        pricing = pricingSchemes[scheme] ?: return false
        return true
    }

    private fun vehicleOf(name: String): VehicleType? = VehicleType.entries.firstOrNull { it.name == name }
}

class ParkingLot(spots: Int) {
    private val occupied = BooleanArray(spots)
    private val spotOf = HashMap<String, Int>()

    fun park(plate: String): Int {
        if (plate in spotOf) {
            return -1
        }
        val spot = occupied.indexOfFirst { !it }
        if (spot == -1) {
            return -1
        }
        occupied[spot] = true
        spotOf[plate] = spot
        return spot
    }

    fun leave(plate: String): Boolean {
        val spot = spotOf.remove(plate) ?: return false
        occupied[spot] = false
        return true
    }

    fun available(): Int = occupied.size - spotOf.size
}

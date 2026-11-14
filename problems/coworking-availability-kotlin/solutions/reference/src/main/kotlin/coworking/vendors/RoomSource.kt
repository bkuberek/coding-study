package coworking.vendors

import java.time.LocalDate
import kotlinx.serialization.Serializable

/** One slot a member can book, and the vendor a booking goes to. */
@Serializable
data class Slot(val room: String, val start: String, val end: String, val vendor: String)

/** A vendor gave no usable answer: every way a vendor can fail ends as this. */
class VendorUnavailable(message: String, cause: Throwable? = null) : Exception(message, cause)

/** The seam between the API and its vendors: what every vendor looks like. */
interface RoomSource {
    val name: String

    /** What can be booked on [day]; throws [VendorUnavailable] without a usable answer. */
    suspend fun openSlots(day: LocalDate): List<Slot>
}

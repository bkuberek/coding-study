package coworking

import coworking.vendors.RoomSource
import coworking.vendors.Slot
import coworking.vendors.VendorUnavailable
import java.lang.System.Logger.Level
import java.time.LocalDate
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.serialization.Serializable

private val log = System.getLogger("coworking.availability")

/** One answer from any number of vendors, none of which can take another down. */
@Serializable
data class RoomAvailability(val slots: List<Slot>, val unavailable: List<String>)

/**
 * Asks every vendor at once, each in a coroutine of its own; one with no usable answer goes in
 * `unavailable`. Any other exception is a bug, and cancels the rest.
 */
suspend fun roomAvailability(day: LocalDate, vendors: List<RoomSource>): RoomAvailability =
    coroutineScope {
        val answers = vendors.map { vendor -> async { vendor.answerOn(day) } }.awaitAll()
        RoomAvailability(
            slots = answers.filterIsInstance<VendorAnswer.Slots>()
                .flatMap { it.slots }
                .sortedWith(compareBy({ it.start }, { it.room })),
            unavailable = answers.filterIsInstance<VendorAnswer.Unavailable>().map { it.name }.sorted(),
        )
    }

private sealed interface VendorAnswer {
    data class Slots(val slots: List<Slot>) : VendorAnswer

    data class Unavailable(val name: String) : VendorAnswer
}

private suspend fun RoomSource.answerOn(day: LocalDate): VendorAnswer =
    try {
        VendorAnswer.Slots(openSlots(day))
    } catch (reason: VendorUnavailable) {
        log.log(Level.WARNING, "{0} is unavailable: {1}", name, reason.message)
        VendorAnswer.Unavailable(name)
    }

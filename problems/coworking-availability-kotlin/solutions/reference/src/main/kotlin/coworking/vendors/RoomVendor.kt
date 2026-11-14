package coworking.vendors

import java.net.URI
import java.time.LocalDate
import kotlin.time.Duration
import kotlin.time.Duration.Companion.milliseconds
import kotlin.time.Duration.Companion.seconds
import kotlinx.serialization.Serializable

/** The vendor of the main building's rooms: what it speaks, and when to ask it again. */
class RoomVendor(baseUrl: URI) : RoomSource {
    override val name = NAME
    private val availability = baseUrl.resolve("/v1/rooms/availability")

    override suspend fun openSlots(day: LocalDate): List<Slot> {
        val uri = URI.create("$availability?date=$day")
        val answer = askWithRetries(MAX_REQUESTS, ::waitBeforeRetry) { fetch(uri) }
        if (!answer.ok) throw VendorUnavailable("$NAME answered ${answer.status}")
        return answer.decode(Rooms.serializer(), NAME).rooms.flatMap { room ->
            room.slots.filter { it.isOpen }.map { Slot(room.id, it.start!!, it.end!!, NAME) }
        }
    }

    internal companion object {
        const val NAME = "room-vendor"
        const val MAX_REQUESTS = 3
        val SHORT_WAIT = 200.milliseconds
        private const val TOO_MANY_REQUESTS = 429
        private const val SERVER_ERROR = 500
        private val WHOLE_SECONDS = Regex("[0-9]{1,9}")

        /** How long to wait before asking again; null when asking again will not help. */
        fun waitBeforeRetry(answer: Answer): Duration? =
            when {
                answer.status == TOO_MANY_REQUESTS ->
                    answer.headers.firstValue("Retry-After").orElse(null)?.wholeSeconds() ?: SHORT_WAIT
                answer.status >= SERVER_ERROR -> SHORT_WAIT
                else -> null
            }

        private fun String.wholeSeconds(): Duration? = takeIf { WHOLE_SECONDS.matches(it) }?.toLong()?.seconds
    }

    /** Its answer, as its API documents it. */
    @Serializable
    private data class Rooms(val rooms: List<Room>)

    @Serializable
    private data class Room(val id: String, val slots: List<RoomSlot>)

    /** A slot whose status is not open may leave out its times. */
    @Serializable
    private data class RoomSlot(val status: String, val start: String? = null, val end: String? = null) {
        val isOpen: Boolean get() = status == OPEN

        init {
            require(!isOpen || (start != null && end != null)) { "an open slot without its times" }
        }

        private companion object {
            const val OPEN = "open"
        }
    }
}

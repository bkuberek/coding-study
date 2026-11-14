package coworking.vendors

import java.net.URI
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import kotlin.time.Duration
import kotlin.time.Duration.Companion.milliseconds
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** The vendor of the building next door, which says most things in the body of a 200. */
class AnnexVendor(baseUrl: URI) : RoomSource {
    override val name = NAME
    private val spaces = baseUrl.resolve("/v2/spaces/open")

    override suspend fun openSlots(day: LocalDate): List<Slot> {
        val uri = URI.create("$spaces?day=${day.format(DateTimeFormatter.BASIC_ISO_DATE)}")
        val answer = askWithRetries(MAX_REQUESTS, ::waitBeforeRetry) { body(uri) }
        val result = answer.result?.takeIf { answer.ok }
            ?: throw VendorUnavailable("$NAME gave no spaces: $answer")
        return result.spaces.flatMap { space -> space.open.map { space.slot(it) } }
    }

    /** Its 5xx means down for maintenance, so any status but 2xx ends the asking. */
    private suspend fun body(uri: URI): AnnexAnswer {
        val answer = fetch(uri)
        if (!answer.ok) throw VendorUnavailable("$NAME answered ${answer.status}")
        return answer.decode(AnnexAnswer.serializer(), NAME)
    }

    internal companion object {
        const val NAME = "annex-vendor"
        const val MAX_REQUESTS = 2
        private const val BUSY = "BUSY"
        private const val MINUTES_PER_HOUR = 60

        /** How long it asks you to wait before asking again; null if it does not ask. */
        fun waitBeforeRetry(answer: AnnexAnswer): Duration? =
            answer.error?.takeIf { !answer.ok && it.code == BUSY }?.retryAfterMs?.milliseconds

        /** Times come as minutes past midnight. */
        private fun clock(minutesPastMidnight: Int): String =
            "%02d:%02d".format(minutesPastMidnight / MINUTES_PER_HOUR, minutesPastMidnight % MINUTES_PER_HOUR)

        private fun Space.slot(window: Window) =
            Slot(code, clock(window.fromMinute), clock(window.fromMinute + window.minutes), NAME)
    }

    /** Its answer, as its API documents it: a result when ok, an error when not. */
    @Serializable
    internal data class AnnexAnswer(val ok: Boolean, val result: Spaces? = null, val error: Failure? = null)

    @Serializable
    internal data class Spaces(val spaces: List<Space>)

    @Serializable
    internal data class Space(val code: String, val open: List<Window>)

    @Serializable
    internal data class Window(@SerialName("from_minute") val fromMinute: Int, val minutes: Int)

    @Serializable
    internal data class Failure(val code: String, @SerialName("retry_after_ms") val retryAfterMs: Double? = null)
}

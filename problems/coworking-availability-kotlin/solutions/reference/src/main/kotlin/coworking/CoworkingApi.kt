package coworking

import coworking.vendors.RoomSource
import java.net.URI
import java.time.LocalDate
import kotlinx.serialization.Serializable

/** Every answer the API gives, from a request's method and target; no HTTP. */
class CoworkingApi(private val desks: DeskInventory, private val vendors: List<RoomSource>) {
    suspend fun answer(method: String, target: URI): Reply {
        val route = Route.entries.find { it.path == target.path } ?: return refusal(404, "not found")
        if (method != GET) return refusal(405, "method not allowed")
        val date = target.queryValue("date")
        return when (route) {
            Route.HEALTH -> reply(200, Status("ok"))
            Route.DESKS -> desksOn(date)
            Route.AVAILABILITY -> availabilityOn(date)
        }
    }

    private fun desksOn(text: String): Reply =
        when (val day = onSale(text)) {
            is OnSale.Refused -> day.reply
            is OnSale.Day -> reply(200, DeskCount(text, day.available))
        }

    private suspend fun availabilityOn(text: String): Reply =
        when (val day = onSale(text)) {
            is OnSale.Refused -> day.reply
            is OnSale.Day -> {
                val rooms = roomAvailability(day.date, vendors)
                reply(200, Availability(text, Desks(day.available), rooms))
            }
        }

    /** The day [text] names and its desks left, or why this API refuses it, before a vendor hears of it. */
    private fun onSale(text: String): OnSale {
        if (text.isEmpty()) return OnSale.Refused(refusal(400, "date is required"))
        val date = parseDay(text)
            ?: return OnSale.Refused(refusal(400, "date must be a real day, as YYYY-MM-DD"))
        val available = desks.availableOn(text)
            ?: return OnSale.Refused(refusal(404, "no desks on sale for that date"))
        return OnSale.Day(date, available)
    }

    private enum class Route(val path: String) {
        HEALTH("/health"),
        DESKS("/desks"),
        AVAILABILITY("/availability"),
    }

    private sealed interface OnSale {
        data class Day(val date: LocalDate, val available: Int) : OnSale

        data class Refused(val reply: Reply) : OnSale
    }

    private companion object {
        const val GET = "GET"
    }
}

@Serializable
data class DeskCount(val date: String, val available: Int)

@Serializable
data class Desks(val available: Int)

@Serializable
data class Availability(val date: String, val desks: Desks, val rooms: RoomAvailability)

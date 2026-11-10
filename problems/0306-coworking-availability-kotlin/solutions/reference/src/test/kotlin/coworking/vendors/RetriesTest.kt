package coworking.vendors

import coworking.vendors.AnnexVendor.AnnexAnswer
import coworking.vendors.AnnexVendor.Failure
import coworking.vendors.AnnexVendor.Spaces
import java.net.http.HttpHeaders
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.time.Duration.Companion.milliseconds
import kotlin.time.Duration.Companion.seconds

class RetriesTest {
    private fun answer(status: Int, retryAfter: String? = null): Answer {
        val headers = retryAfter?.let { mapOf("Retry-After" to listOf(it)) } ?: emptyMap()
        return Answer(status, HttpHeaders.of(headers) { _, _ -> true }, ByteArray(0))
    }

    @Test
    fun a429WaitsAsLongAsItSays() {
        assertEquals(2.seconds, RoomVendor.waitBeforeRetry(answer(429, retryAfter = "2")))
    }

    @Test
    fun waitsALittle() {
        val passing = listOf(answer(429), answer(429, "soon"), answer(429, "-1"), answer(500), answer(503))
        for (found in passing) {
            assertEquals(RoomVendor.SHORT_WAIT, RoomVendor.waitBeforeRetry(found), "status ${found.status}")
        }
    }

    @Test
    fun askingTheRoomVendorAgainWillNotHelp() {
        for (status in listOf(200, 400, 403, 404)) {
            assertNull(RoomVendor.waitBeforeRetry(answer(status)), "status $status")
        }
    }

    @Test
    fun busyWaitsAsManyMillisecondsAsItSays() {
        val busy = AnnexAnswer(ok = false, error = Failure("BUSY", retryAfterMs = 1500.0))

        assertEquals(1500.milliseconds, AnnexVendor.waitBeforeRetry(busy))
    }

    @Test
    fun askingTheAnnexAgainWillNotHelp() {
        val final = listOf(
            AnnexAnswer(ok = false, error = Failure("DAY_CLOSED")),
            AnnexAnswer(ok = false, error = Failure("BUSY")),
            AnnexAnswer(ok = true, result = Spaces(emptyList())),
        )
        for (found in final) {
            assertNull(AnnexVendor.waitBeforeRetry(found), "$found")
        }
    }
}

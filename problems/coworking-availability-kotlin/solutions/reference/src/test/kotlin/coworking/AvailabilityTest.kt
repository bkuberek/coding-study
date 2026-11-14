package coworking

import kotlin.test.AfterTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject

class AvailabilityTest {
    private val app = App()
    private val vendors = Vendors()

    @AfterTest
    fun resetTheVendors() {
        vendors.reset()
    }

    private fun roomsOn(day: String): Map<String, JsonElement> {
        val answer = app.get("/availability?date=$day")
        assertEquals(200, answer.status)
        return answer.body.jsonObject.getValue("rooms").jsonObject
    }

    @Test
    fun bothVendorsAnswerInOneList() {
        val rooms = roomsOn("2027-03-08")

        assertEquals(5, rooms.getValue("slots").jsonArray.size)
        assertEquals(json("[]"), rooms["unavailable"])
    }

    @Test
    fun aVendorThatIsDownCostsOnlyItsOwnSlots() {
        vendors.setScenario("room-vendor", "outage")

        val rooms = roomsOn("2027-03-08")

        assertEquals(3, rooms.getValue("slots").jsonArray.size)
        assertEquals(json("""["room-vendor"]"""), rooms["unavailable"])
    }

    @Test
    fun bothVendorsDownStillAnswersTheDesks() {
        vendors.setScenario("room-vendor", "outage")
        vendors.setScenario("annex-vendor", "maintenance")

        val expected = App.Answer(
            200,
            json(
                """
                {
                  "date": "2027-03-08",
                  "desks": {"available": 20},
                  "rooms": {"slots": [], "unavailable": ["annex-vendor", "room-vendor"]}
                }
                """,
            ),
        )

        assertEquals(expected, app.get("/availability?date=2027-03-08"))
    }
}

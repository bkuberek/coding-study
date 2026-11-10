package coworking

import kotlin.test.Test
import kotlin.test.assertEquals

class DesksTest {
    private val app = App()

    @Test
    fun theServiceAnswersItsHealthPath() {
        assertEquals(200, app.get("/health").status)
    }

    @Test
    fun aDayOnSaleAnswersItsCount() {
        val expected = App.Answer(200, json("""{"date": "2027-03-01", "available": 12}"""))

        assertEquals(expected, app.get("/desks?date=2027-03-01"))
    }

    @Test
    fun noDateIsABadRequest() {
        val expected = App.Answer(400, json("""{"error": "date is required"}"""))

        assertEquals(expected, app.get("/desks"))
    }
}

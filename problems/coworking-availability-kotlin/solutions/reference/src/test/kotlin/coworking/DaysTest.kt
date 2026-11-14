package coworking

import java.time.LocalDate
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class DaysTest {
    @Test
    fun aRealDayIsThatDay() {
        assertEquals(LocalDate.of(2027, 3, 1), parseDay("2027-03-01"))
    }

    @Test
    fun aLeapDayIsRealInALeapYear() {
        assertEquals(LocalDate.of(2028, 2, 29), parseDay("2028-02-29"))
    }

    @Test
    fun namesNoDay() {
        val notDays = listOf(
            "2027-02-30", "2027-02-29", "2027-13-01", "2027-3-1", "20270301", "+12027-03-01", "2027-03-01\n", "soon",
        )
        for (text in notDays) {
            assertNull(parseDay(text), "'$text' names a day")
        }
    }
}

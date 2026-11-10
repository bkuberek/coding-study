package coworking

import java.time.LocalDate
import java.time.format.DateTimeParseException

private val DAY_FORM = Regex("[0-9]{4}-[0-9]{2}-[0-9]{2}")

/**
 * The day [text] names, written YYYY-MM-DD; null when it names no day in that form. The form comes
 * first: `LocalDate.parse` alone takes `+12027-03-01` as well.
 */
fun parseDay(text: String): LocalDate? {
    if (!DAY_FORM.matches(text)) return null
    return try {
        LocalDate.parse(text)
    } catch (noSuchDay: DateTimeParseException) {
        null
    }
}

package coworking

import java.nio.file.Path
import kotlin.io.path.readText
import kotlinx.serialization.json.Json

/** The hot desks the space holds itself: how many are left on each day it sells. */
class DeskInventory(private val byDay: Map<String, Int>) {
    /** Desks left on [day], written YYYY-MM-DD; null when it is not on sale. */
    fun availableOn(day: String): Int? = byDay[day]

    companion object {
        fun fromFile(path: Path): DeskInventory =
            DeskInventory(Json.decodeFromString<Map<String, Int>>(path.readText()))
    }
}

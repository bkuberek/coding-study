import java.time.LocalDate
import java.util.TreeMap

private class FieldHistory {
    private val writeTimes = ArrayList<Long>() // every write, in timestamp order
    private val writeDates = ArrayList<LocalDate>()
    private val writeValues = ArrayList<String>()
    private val view = TreeMap<LocalDate, String>() // current view: one value per effective date

    fun write(timestamp: Long, effectiveDate: LocalDate, value: String) {
        writeTimes.add(timestamp)
        writeDates.add(effectiveDate)
        writeValues.add(value)
        view[effectiveDate] = value // a correction replaces the value for that date
    }

    fun current(onDate: LocalDate): String = view.floorEntry(onDate)?.value ?: ""

    fun asKnown(onDate: LocalDate, knownAt: Long): String {
        var bestDate: LocalDate? = null
        var bestValue = ""
        for (i in 0 until countKnown(knownAt)) {
            val effectiveDate = writeDates[i]
            // >= lets a later write for the same date replace an earlier one
            if (effectiveDate <= onDate && (bestDate == null || effectiveDate >= bestDate)) {
                bestDate = effectiveDate
                bestValue = writeValues[i]
            }
        }
        return bestValue
    }

    // Number of writes made at or before knownAt (timestamps are sorted and distinct).
    private fun countKnown(knownAt: Long): Int {
        var low = 0
        var high = writeTimes.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (writeTimes[middle] <= knownAt) low = middle + 1 else high = middle
        }
        return low
    }
}

class RecordHistory {
    private val records = HashMap<String, TreeMap<String, FieldHistory>>()

    fun setValue(timestamp: Long, recordId: String, field: String, effectiveDate: LocalDate, value: String) {
        records.getOrPut(recordId) { TreeMap() }
            .getOrPut(field) { FieldHistory() }
            .write(timestamp, effectiveDate, value)
    }

    fun getValue(timestamp: Long, recordId: String, field: String, onDate: LocalDate): String =
        records[recordId]?.get(field)?.current(onDate) ?: ""

    fun snapshot(timestamp: Long, recordId: String, onDate: LocalDate): List<String> =
        snapshotWith(recordId) { it.current(onDate) }

    fun getValueAsKnown(timestamp: Long, recordId: String, field: String, onDate: LocalDate, knownAt: Long): String =
        records[recordId]?.get(field)?.asKnown(onDate, knownAt) ?: ""

    fun snapshotAsKnown(timestamp: Long, recordId: String, onDate: LocalDate, knownAt: Long): List<String> =
        snapshotWith(recordId) { it.asKnown(onDate, knownAt) }

    private fun snapshotWith(recordId: String, read: (FieldHistory) -> String): List<String> = buildList {
        // The TreeMap iterates the field names in sorted order.
        for ((field, history) in records[recordId].orEmpty()) {
            val value = read(history)
            if (value.isNotEmpty()) add("$field=$value")
        }
    }
}

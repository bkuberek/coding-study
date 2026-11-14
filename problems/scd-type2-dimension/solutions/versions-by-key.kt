import java.util.TreeMap

private const val OPEN_END = 99991231
private const val UNKNOWN_MEMBER = 0

private class Version(
    val key: Int,
    val businessKey: String,
    val values: MutableList<String>,
    val validFrom: Int,
    var validTo: Int,
) {
    fun row(): List<String> =
        listOf(key.toString(), businessKey) + values +
            listOf(validFrom.toString(), validTo.toString(), if (validTo == OPEN_END) "Y" else "N")
}

/**
 * Every business key keeps its versions in a list sorted by validFrom, and the versions never
 * overlap, so the version valid at a date is one binary search away. Untracked attributes hold one
 * value per business key, copied into every version, and the date of the latest load that carried
 * the key decides whether a row may still overwrite them.
 */
class DimensionTable(attributes: List<String>) {
    private val position: Map<String, Int> = attributes.withIndex().associate { it.value to it.index }
    private val tracked = mutableListOf<Int>()
    private val bySurrogate = HashMap<Int, Version>()
    private val versions = TreeMap<String, MutableList<Version>>()
    private val lastLoad = HashMap<String, Int>()
    private var nextKey = 1

    // Level 1
    fun load(rows: List<List<String>>, loadDate: Int): List<Int> = apply(rows, loadDate).first

    fun lookup(businessKey: String): Int {
        val last = versions[businessKey]?.last() ?: return -1
        return if (last.validTo == OPEN_END) last.key else -1
    }

    fun rowOf(surrogateKey: Int): List<String> = bySurrogate[surrogateKey]?.row() ?: emptyList()

    fun size(): Int = bySurrogate.size

    // Level 2
    fun trackHistory(attribute: String): Boolean {
        val index = position[attribute] ?: return false
        if (index in tracked) {
            return false
        }
        tracked.add(index)
        return true
    }

    fun history(businessKey: String): List<List<String>> = versions[businessKey].orEmpty().map { it.row() }

    // Level 3
    fun lookupAt(businessKey: String, asOf: Int): Int = validAt(businessKey, asOf)?.key ?: -1

    fun snapshotAt(asOf: Int): List<List<String>> = versions.keys.mapNotNull { validAt(it, asOf)?.row() }

    fun resolveFacts(facts: List<List<String>>): List<List<String>> =
        facts.map { (factId, businessKey, eventDate) ->
            if (businessKey !in versions) {
                listOf(factId, UNKNOWN_MEMBER.toString(), "unknown-key")
            } else {
                val version = validAt(businessKey, eventDate.toInt())
                when {
                    version == null -> listOf(factId, UNKNOWN_MEMBER.toString(), "no-version")
                    version.validTo == OPEN_END -> listOf(factId, version.key.toString(), "current")
                    else -> listOf(factId, version.key.toString(), "late")
                }
            }
        }

    // Level 4
    fun loadFull(rows: List<List<String>>, loadDate: Int): List<Int> {
        val (counts, present) = apply(rows, loadDate)
        var closed = 0
        for ((businessKey, list) in versions) {
            val last = list.last()
            if (businessKey !in present && last.validTo == OPEN_END) {
                last.validTo = loadDate
                closed++
            }
        }
        return counts + closed
    }

    fun fullHistory(): List<List<String>> = versions.values.flatMap { list -> list.map { it.row() } }

    // Helpers
    private fun apply(rows: List<List<String>>, loadDate: Int): Pair<List<Int>, Set<String>> {
        val latest = TreeMap<String, List<String>>()
        for (row in rows) {
            latest[row[0]] = row.drop(1)
        }
        var inserted = 0
        var changed = 0
        var unchanged = 0
        for ((businessKey, values) in latest) {
            if (businessKey !in versions) {
                versions[businessKey] = mutableListOf()
                lastLoad[businessKey] = loadDate
                insert(businessKey, values.toMutableList(), loadDate, OPEN_END)
                inserted++
            } else if (merge(businessKey, values, loadDate)) {
                changed++
            } else {
                unchanged++
            }
        }
        return Pair(listOf(inserted, changed, unchanged), latest.keys.toSet())
    }

    private fun merge(businessKey: String, values: List<String>, loadDate: Int): Boolean {
        val list = versions.getValue(businessKey)
        var changed = false
        if (loadDate >= lastLoad.getValue(businessKey)) {
            lastLoad[businessKey] = loadDate
            for (index in position.values.filter { it !in tracked }) {
                if (list[0].values[index] != values[index]) {
                    list.forEach { it.values[index] = values[index] }
                    changed = true
                }
            }
        }
        val holder = validAt(businessKey, loadDate)
        if (holder != null) {
            if (tracked.all { holder.values[it] == values[it] }) {
                return changed
            }
            if (holder.validFrom == loadDate) {
                tracked.forEach { holder.values[it] = values[it] }
                return true
            }
            val end = holder.validTo
            holder.validTo = loadDate
            insert(businessKey, combine(list[0], values), loadDate, end)
            return true
        }
        val end = list.firstOrNull { it.validFrom > loadDate }?.validFrom ?: OPEN_END
        insert(businessKey, combine(list[0], values), loadDate, end)
        return true
    }

    /** The incoming tracked values with the key's untracked values. */
    private fun combine(shared: Version, values: List<String>): MutableList<String> {
        val combined = shared.values.toMutableList()
        tracked.forEach { combined[it] = values[it] }
        return combined
    }

    private fun insert(businessKey: String, values: MutableList<String>, validFrom: Int, validTo: Int) {
        val version = Version(nextKey++, businessKey, values, validFrom, validTo)
        bySurrogate[version.key] = version
        val list = versions.getValue(businessKey)
        list.add(startsAtOrBefore(list, validFrom), version)
    }

    /** The number of versions whose validFrom is at or before the date. */
    private fun startsAtOrBefore(list: List<Version>, date: Int): Int {
        var low = 0
        var high = list.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (list[middle].validFrom <= date) low = middle + 1 else high = middle
        }
        return low
    }

    private fun validAt(businessKey: String, asOf: Int): Version? {
        val list = versions[businessKey] ?: return null
        val at = startsAtOrBefore(list, asOf) - 1
        return if (at < 0 || asOf >= list[at].validTo) null else list[at]
    }
}

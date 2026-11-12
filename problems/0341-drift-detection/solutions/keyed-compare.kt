/**
 * The recorded state maps an address to an id and attributes, and a scan maps an id to a type and
 * attributes. Drift is found by looking each recorded id up in the scan, comparing values after the
 * type's normalization rules, and filtering the rows through the ignore rules. Import adds a
 * recorded entry, the plan compares the desired state with the recorded one, and a reconcile turns
 * each drift row into the action of the newest policy that matches.
 */
class DriftDetector {
    private data class Entry(val tag: String, val attributes: Map<String, String>)

    private data class DriftRow(val row: List<String>, val address: String)

    private val recorded = HashMap<String, Entry>()
    private val observed = HashMap<String, Entry>()
    private val ignores = LinkedHashSet<Pair<String, String>>()
    private val lists = HashSet<String>()
    private val defaults = HashMap<String, String>()
    private val desired = HashMap<String, Map<String, String>>()
    private val policies = LinkedHashMap<String, String>()

    // Level 1
    fun record(address: String, resourceId: String, attributes: List<List<String>>): Boolean =
        recorded.put(address, Entry(resourceId, attributes.associate { it[0] to it[1] })) == null

    fun observe(resourceId: String, resourceType: String, attributes: List<List<String>>): Boolean =
        observed.put(resourceId, Entry(resourceType, attributes.associate { it[0] to it[1] })) == null

    fun drift(): List<List<String>> = driftRows().map { it.row }

    // Level 2
    fun ignore(pattern: String, key: String): Boolean = ignores.add(pattern to key)

    fun unordered(resourceType: String, key: String): Boolean = lists.add("$resourceType.$key")

    fun defaultValue(resourceType: String, key: String, value: String): Boolean =
        defaults.put("$resourceType.$key", value) == null

    // Level 3
    fun importResource(address: String, resourceId: String): String {
        val found = observed[resourceId] ?: return "not-found"
        return when {
            kindOf(address) != found.tag -> "type-mismatch"
            recorded.values.any { it.tag == resourceId } -> "already-managed"
            address in recorded -> "address-taken"
            else -> {
                recorded[address] = Entry(resourceId, HashMap(found.attributes))
                "imported"
            }
        }
    }

    fun desire(address: String, attributes: List<List<String>>): Boolean =
        desired.put(address, attributes.associate { it[0] to it[1] }) == null

    fun plan(): List<List<String>> =
        (desired.keys + recorded.keys).toSortedSet().flatMap { address ->
            val entry = recorded[address]
            val wanted = desired[address]
            when {
                entry == null -> listOf(listOf("create", address))
                wanted == null -> listOf(listOf("delete", address))
                else -> differing(kindOf(address), entry.attributes, wanted).map { key ->
                    listOf("update", address, key, entry.attributes[key] ?: "", wanted[key] ?: "")
                }
            }
        }

    // Level 4
    fun policy(pattern: String, mode: String): Boolean {
        val isNew = policies.remove(pattern) == null
        policies[pattern] = mode
        return isNew
    }

    fun reconcile(): List<List<String>> = driftRows().mapNotNull { (row, address) ->
        if (row[0] == "unmanaged") return@mapNotNull listOf("alert-unmanaged", row[1], row[2])
        val mode = mode(address)
        if (row[0] == "deleted") {
            return@mapNotNull when (mode) {
                "revert" -> listOf("recreate", address)
                "accept" -> listOf("forget", address)
                else -> listOf("alert-deleted", address, row[2])
            }
        }
        val (_, _, key, recordedValue, scanned) = row
        if (mode == "alert") return@mapNotNull listOf("alert", address, key, recordedValue, scanned)
        val wanted = desired.getValue(address)[key] ?: ""
        when {
            same(kindOf(address), key, scanned.ifEmpty { null }, wanted.ifEmpty { null }) -> null
            mode == "revert" -> listOf("revert", address, key, scanned, wanted)
            else -> listOf("accept", address, key, wanted, scanned)
        }
    }

    // Comparing
    private fun kindOf(address: String) = address.substringBefore('.')

    private fun same(resourceType: String, key: String, first: String?, second: String?): Boolean {
        val id = "$resourceType.$key"
        val a = first ?: defaults[id]
        val b = second ?: defaults[id]
        if (a == null || b == null) return a == b
        if (id in lists) return a.split(",").sorted() == b.split(",").sorted()
        return a == b
    }

    private fun differing(resourceType: String, first: Map<String, String>, second: Map<String, String>): List<String> =
        (first.keys + second.keys).sorted().filter { !same(resourceType, it, first[it], second[it]) }

    private fun ignored(text: String, key: String): Boolean =
        ignores.any { (pattern, ruleKey) -> ruleKey == key && glob(pattern, text) }

    private fun mode(address: String): String =
        policies.entries.lastOrNull { glob(it.key, address) }?.value ?: "alert"

    private fun driftRows(): List<DriftRow> {
        val rows = mutableListOf<DriftRow>()
        val managed = HashSet<String>()
        for (address in recorded.keys.sorted()) {
            val entry = recorded.getValue(address)
            managed.add(entry.tag)
            if (ignored(address, "*")) continue
            val found = observed[entry.tag]
            if (found == null) {
                rows.add(DriftRow(listOf("deleted", address, entry.tag), address))
                continue
            }
            for (key in differing(kindOf(address), entry.attributes, found.attributes)) {
                if (!ignored(address, key)) {
                    val row = listOf("changed", address, key, entry.attributes[key] ?: "", found.attributes[key] ?: "")
                    rows.add(DriftRow(row, address))
                }
            }
        }
        for (resourceId in observed.keys.sorted()) {
            val resourceType = observed.getValue(resourceId).tag
            if (resourceId !in managed && !ignored("$resourceType.$resourceId", "*")) {
                rows.add(DriftRow(listOf("unmanaged", resourceId, resourceType), ""))
            }
        }
        return rows
    }

    private companion object {
        /** Whether [text] matches [pattern], where `*` stands for any run of characters. */
        fun glob(pattern: String, text: String): Boolean {
            var p = 0
            var t = 0
            var star = -1
            var mark = 0
            while (t < text.length) {
                if (p < pattern.length && pattern[p] != '*' && pattern[p] == text[t]) {
                    p++
                    t++
                } else if (p < pattern.length && pattern[p] == '*') {
                    star = p
                    mark = t
                    p++
                } else if (star >= 0) {
                    mark++
                    p = star + 1
                    t = mark
                } else {
                    return false
                }
            }
            while (p < pattern.length && pattern[p] == '*') p++
            return p == pattern.length
        }
    }
}

import java.util.TreeMap

/** One write to a field: a value (null for a deletion), from [since] until [expiresAt]. */
private data class Version(val since: Long, val value: String?, val expiresAt: Long?) {
    fun visibleAt(moment: Long): Boolean = value != null && (expiresAt == null || moment < expiresAt)
}

/** Every version of one field; timestamps arrive in increasing order, so a TreeMap by time is exact. */
private class FieldHistory {
    private val versions = TreeMap<Long, Version>()

    fun record(version: Version) {
        versions[version.since] = version
    }

    fun valueAt(moment: Long): String? = versions.floorEntry(moment)?.value?.takeIf { it.visibleAt(moment) }?.value
}

class InMemoryDatabase {
    private val records = HashMap<String, HashMap<String, FieldHistory>>()

    // Level 1
    fun set(timestamp: Long, key: String, field: String, value: String) {
        write(key, field, Version(timestamp, value, null))
    }

    fun get(timestamp: Long, key: String, field: String): String = valueAt(key, field, timestamp) ?: ""

    fun remove(timestamp: Long, key: String, field: String): Boolean {
        if (valueAt(key, field, timestamp) == null) {
            return false
        }
        write(key, field, Version(timestamp, null, null))
        return true
    }

    // Level 2
    fun scan(timestamp: Long, key: String): List<String> = scanFields(key, "", timestamp)

    fun scanByPrefix(timestamp: Long, key: String, prefix: String): List<String> = scanFields(key, prefix, timestamp)

    // Level 3
    fun setWithTtl(timestamp: Long, key: String, field: String, value: String, ttl: Long) {
        write(key, field, Version(timestamp, value, timestamp + ttl))
    }

    // Level 4
    fun getAt(timestamp: Long, key: String, field: String, atTimestamp: Long): String =
        valueAt(key, field, atTimestamp) ?: ""

    fun scanAt(timestamp: Long, key: String, atTimestamp: Long): List<String> = scanFields(key, "", atTimestamp)

    private fun write(key: String, field: String, version: Version) {
        records.getOrPut(key) { HashMap() }.getOrPut(field) { FieldHistory() }.record(version)
    }

    private fun valueAt(key: String, field: String, moment: Long): String? = records[key]?.get(field)?.valueAt(moment)

    private fun scanFields(key: String, prefix: String, moment: Long): List<String> =
        records[key].orEmpty()
            .filterKeys { it.startsWith(prefix) }
            .mapNotNull { (field, history) -> history.valueAt(moment)?.let { field to it } }
            .sortedBy { it.first }
            .map { (field, value) -> "$field($value)" }
}

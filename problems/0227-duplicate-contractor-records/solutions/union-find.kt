private val LEGAL_FORMS = setOf("co", "company", "corp", "inc", "incorporated", "llc", "ltd")
private val SEPARATORS = Regex("[^a-z0-9]+")
private const val TAX_ID_DIGITS = 9

class Solution {
    fun duplicateGroups(names: Array<String>, taxIds: Array<String>): List<List<Int>> {
        val parent = IntArray(names.size) { it }

        fun find(start: Int): Int {
            var record = start
            while (parent[record] != record) {
                parent[record] = parent[parent[record]] // path halving
                record = parent[record]
            }
            return record
        }

        // Two key spaces: a name never matches a tax id.
        val firstWithName = HashMap<String, Int>()
        val firstWithTaxId = HashMap<String, Int>()
        fun link(firstWithKey: HashMap<String, Int>, key: String, record: Int) {
            if (key.isEmpty()) return // an empty key matches nothing
            val first = firstWithKey.putIfAbsent(key, record)
            if (first != null) parent[find(record)] = find(first)
        }

        for (record in names.indices) {
            link(firstWithName, normalizeName(names[record]), record)
            link(firstWithTaxId, normalizeTaxId(taxIds[record]), record)
        }
        // groupBy keeps first-seen order, so the groups come out by smallest index.
        return names.indices.groupBy { find(it) }.values.filter { it.size > 1 }
    }

    private fun normalizeName(name: String): String {
        val words = name.lowercase().split(SEPARATORS).filter { it.isNotEmpty() }.toMutableList()
        while (words.isNotEmpty() && words.last() in LEGAL_FORMS) {
            words.removeAt(words.lastIndex)
        }
        return words.joinToString(" ")
    }

    private fun normalizeTaxId(taxId: String): String {
        val digits = taxId.filter { it in '0'..'9' }
        return if (digits.length == TAX_ID_DIGITS) digits else ""
    }
}

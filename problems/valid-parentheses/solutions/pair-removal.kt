private val PAIRS = listOf("()", "[]", "{}")

class Solution {
    fun isValid(s: String): Boolean {
        var current = s
        while (true) {
            val shorter = PAIRS.fold(current) { text, pair -> text.replace(pair, "") }
            if (shorter.length == current.length) {
                // Nothing left to delete: balanced exactly when nothing is left at all.
                return current.isEmpty()
            }
            current = shorter
        }
    }
}

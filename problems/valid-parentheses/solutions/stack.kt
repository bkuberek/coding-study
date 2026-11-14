private val OPENER_OF = mapOf(')' to '(', ']' to '[', '}' to '{')

class Solution {
    fun isValid(s: String): Boolean {
        val openBrackets = ArrayDeque<Char>()
        for (character in s) {
            val opener = OPENER_OF[character]
            if (opener == null) {
                openBrackets.addLast(character)
            } else if (openBrackets.removeLastOrNull() != opener) {
                return false
            }
        }
        return openBrackets.isEmpty()
    }
}

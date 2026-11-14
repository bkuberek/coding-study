class Solution {
    fun decodeString(s: String): String {
        // For every open group: its repeat count and the text built before its '['.
        val counts = ArrayDeque<Int>()
        val outerTexts = ArrayDeque<StringBuilder>()
        var current = StringBuilder()
        var count = 0
        for (character in s) {
            when {
                character.isDigit() -> count = count * 10 + (character - '0')
                character == '[' -> {
                    counts.addLast(count)
                    outerTexts.addLast(current)
                    current = StringBuilder()
                    count = 0
                }
                character == ']' -> {
                    val outer = outerTexts.removeLast()
                    outer.append(current.toString().repeat(counts.removeLast()))
                    current = outer
                }
                else -> current.append(character)
            }
        }
        return current.toString()
    }
}

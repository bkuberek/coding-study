class Solution {
    fun minRemoveToMakeValid(s: String): String {
        // Pass 1, left to right: drop every closer that finds nothing open.
        val kept = StringBuilder(s.length)
        var openCount = 0
        for (character in s) {
            if (character == ')') {
                if (openCount == 0) {
                    continue
                }
                openCount--
            } else if (character == '(') {
                openCount++
            }
            kept.append(character)
        }
        // Pass 2, right to left: drop the last openCount openers, which are never closed.
        val result = StringBuilder(kept.length)
        for (i in kept.indices.reversed()) {
            if (kept[i] == '(' && openCount > 0) {
                openCount--
                continue
            }
            result.append(kept[i])
        }
        return result.reverse().toString()
    }
}

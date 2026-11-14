class Solution {
    fun minRemoveToMakeValid(s: String): String {
        val text = StringBuilder(s)
        while (true) {
            val position = firstOffender(text)
            if (position == -1) {
                return text.toString()
            }
            text.deleteCharAt(position) // shifts the rest of the text: O(n)
        }
    }

    // A parenthesis that cannot be matched, or -1 when the text is balanced.
    private fun firstOffender(text: CharSequence): Int {
        var depth = 0
        for ((position, character) in text.withIndex()) {
            if (character == '(') {
                depth++
            } else if (character == ')') {
                if (depth == 0) {
                    return position // a closer with nothing open before it
                }
                depth--
            }
        }
        if (depth == 0) {
            return -1
        }
        // Some openers are never closed: the last opener with no closer left after it is one.
        var closers = 0
        for (position in text.indices.reversed()) {
            if (text[position] == ')') {
                closers++
            } else if (text[position] == '(') {
                if (closers == 0) {
                    return position
                }
                closers--
            }
        }
        return -1
    }
}

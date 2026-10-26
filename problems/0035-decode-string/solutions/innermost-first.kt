class Solution {
    fun decodeString(s: String): String {
        var text = s
        while ('[' in text) {
            // The first ']' closes an innermost group: the last '[' before it is its opener.
            val close = text.indexOf(']')
            val open = text.lastIndexOf('[', close)
            var start = open
            while (start > 0 && text[start - 1].isDigit()) {
                start--
            }
            val count = text.substring(start, open).toInt()
            text = text.substring(0, start) + text.substring(open + 1, close).repeat(count) + text.substring(close + 1)
        }
        return text
    }
}

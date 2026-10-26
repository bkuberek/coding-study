private const val MARKER = '#'

class Solution {
    fun encodeDecode(strs: Array<String>): Array<String> = decode(encode(strs))

    private fun encode(strs: Array<String>): String =
        buildString {
            for (text in strs) {
                append(text.length)
                append(MARKER)
                append(text)
            }
        }

    private fun decode(encoded: String): Array<String> {
        val strs = mutableListOf<String>()
        var position = 0
        while (position < encoded.length) {
            // A length has only digits, so the first marker after it ends the length.
            val marker = encoded.indexOf(MARKER, position)
            val start = marker + 1
            val end = start + encoded.substring(position, marker).toInt()
            strs.add(encoded.substring(start, end))
            position = end
        }
        return strs.toTypedArray()
    }
}

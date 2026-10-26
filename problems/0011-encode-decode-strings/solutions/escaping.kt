private const val ESCAPE = '\\'
private const val TERMINATOR = ','

class Solution {
    fun encodeDecode(strs: Array<String>): Array<String> = decode(encode(strs))

    private fun encode(strs: Array<String>): String =
        buildString {
            for (text in strs) {
                for (character in text) {
                    if (character == ESCAPE || character == TERMINATOR) {
                        append(ESCAPE)
                    }
                    append(character)
                }
                append(TERMINATOR)
            }
        }

    private fun decode(encoded: String): Array<String> {
        val strs = mutableListOf<String>()
        val current = StringBuilder()
        var escaped = false
        for (character in encoded) {
            when {
                escaped -> {
                    current.append(character)
                    escaped = false
                }
                character == ESCAPE -> escaped = true
                character == TERMINATOR -> {
                    strs.add(current.toString())
                    current.setLength(0)
                }
                else -> current.append(character)
            }
        }
        return strs.toTypedArray()
    }
}

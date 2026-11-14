class Solution {
    fun decodeString(s: String): String {
        var position = 0

        // Decode up to the ']' that closes the current group, or to the end of the string.
        fun decodeGroup(): String =
            buildString {
                var count = 0
                while (position < s.length) {
                    val character = s[position++]
                    when {
                        character.isDigit() -> count = count * 10 + (character - '0')
                        character == '[' -> {
                            append(decodeGroup().repeat(count))
                            count = 0
                        }
                        character == ']' -> break
                        else -> append(character)
                    }
                }
            }

        return decodeGroup()
    }
}

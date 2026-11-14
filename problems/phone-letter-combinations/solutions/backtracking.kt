private val KEYPAD = mapOf(
    '2' to "abc",
    '3' to "def",
    '4' to "ghi",
    '5' to "jkl",
    '6' to "mno",
    '7' to "pqrs",
    '8' to "tuv",
    '9' to "wxyz",
)

class Solution {
    fun letterCombinations(digits: String): List<String> {
        if (digits.isEmpty()) return emptyList()
        val words = mutableListOf<String>()
        val letters = CharArray(digits.length)

        fun fill(slot: Int) {
            if (slot == digits.length) {
                words.add(String(letters))
                return
            }
            for (letter in KEYPAD.getValue(digits[slot])) {
                letters[slot] = letter
                fill(slot + 1)
            }
        }

        fill(0)
        return words
    }
}

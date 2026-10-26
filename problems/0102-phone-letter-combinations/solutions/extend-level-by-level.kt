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
        return digits.fold(listOf("")) { words, digit ->
            words.flatMap { word -> KEYPAD.getValue(digit).map { letter -> word + letter } }
        }
    }
}

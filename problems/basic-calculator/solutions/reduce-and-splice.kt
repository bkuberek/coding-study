private val LEVELS = listOf("*/", "+-")
private val TOKEN = Regex("""\d+|[-+*/]""")

class Solution {
    fun calculate(s: String): Int {
        val tokens = TOKEN.findAll(s).map { it.value }.toList()
        val values = tokens.filterIndexed { i, _ -> i % 2 == 0 }.mapTo(ArrayList()) { it.toInt() }
        // operators[i] joins values[i] and values[i + 1]
        val operators = tokens.filterIndexed { i, _ -> i % 2 == 1 }.mapTo(ArrayList()) { it[0] }
        for (level in LEVELS) {
            while (true) {
                // indexOfFirst scans from the front every time: O(n) per reduction.
                val position = operators.indexOfFirst { it in level }
                if (position == -1) {
                    break
                }
                values[position] = apply(operators[position], values[position], values[position + 1])
                values.removeAt(position + 1)
                operators.removeAt(position)
            }
        }
        return values[0]
    }

    private fun apply(operator: Char, left: Int, right: Int): Int =
        when (operator) {
            '+' -> left + right
            '-' -> left - right
            '*' -> left * right
            else -> left / right // Int division truncates toward zero
        }
}

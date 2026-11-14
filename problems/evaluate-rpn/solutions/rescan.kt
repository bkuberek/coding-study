private val OPERATORS = setOf("+", "-", "*", "/")

class Solution {
    fun evalRPN(tokens: Array<String>): Int {
        // Operators stay as strings; numbers are parsed once and stored as Ints.
        val items = ArrayList<Any>(tokens.size)
        for (token in tokens) {
            items.add(if (token in OPERATORS) token else token.toInt())
        }
        while (items.size > 1) {
            // The leftmost operator always has its two operands directly in front of it.
            val position = items.indexOfFirst { it is String }
            val left = items[position - 2] as Int
            val right = items[position - 1] as Int
            val result = apply(items[position] as String, left, right)
            items.subList(position - 2, position + 1).clear()
            items.add(position - 2, result)
        }
        return items[0] as Int
    }

    private fun apply(operator: String, left: Int, right: Int): Int =
        when (operator) {
            "+" -> left + right
            "-" -> left - right
            "*" -> left * right
            else -> left / right // Int division truncates toward zero
        }
}

class Solution {
    fun evalRPN(tokens: Array<String>): Int {
        val operands = ArrayDeque<Int>()
        for (token in tokens) {
            when (token) {
                "+", "-", "*", "/" -> {
                    val right = operands.removeLast()
                    val left = operands.removeLast()
                    operands.addLast(apply(token, left, right))
                }
                else -> operands.addLast(token.toInt())
            }
        }
        return operands.last()
    }

    private fun apply(operator: String, left: Int, right: Int): Int =
        when (operator) {
            "+" -> left + right
            "-" -> left - right
            "*" -> left * right
            else -> left / right // Int division truncates toward zero
        }
}

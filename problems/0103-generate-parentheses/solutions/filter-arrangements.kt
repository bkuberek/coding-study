class Solution {
    fun generateParenthesis(n: Int): List<String> {
        val result = mutableListOf<String>()
        val brackets = CharArray(2 * n)

        // Writes every arrangement of the remaining brackets, without looking at their order.
        fun arrange(position: Int, openingLeft: Int, closingLeft: Int) {
            if (position == brackets.size) {
                if (isBalanced(brackets)) result.add(String(brackets))
                return
            }
            if (openingLeft > 0) {
                brackets[position] = '('
                arrange(position + 1, openingLeft - 1, closingLeft)
            }
            if (closingLeft > 0) {
                brackets[position] = ')'
                arrange(position + 1, openingLeft, closingLeft - 1)
            }
        }

        arrange(0, n, n)
        return result
    }

    private fun isBalanced(brackets: CharArray): Boolean {
        // depth is the height a stack of unmatched '(' would have.
        var depth = 0
        for (bracket in brackets) {
            depth += if (bracket == '(') 1 else -1
            if (depth < 0) return false
        }
        return depth == 0
    }
}

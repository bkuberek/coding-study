class Solution {
    fun generateParenthesis(n: Int): List<String> {
        val result = mutableListOf<String>()
        val brackets = StringBuilder(2 * n)

        fun extend(opened: Int, closed: Int) {
            if (closed == n) {
                result.add(brackets.toString())
                return
            }
            if (opened < n) {
                brackets.append('(')
                extend(opened + 1, closed)
                brackets.deleteCharAt(brackets.length - 1)
            }
            // A ')' is allowed only while it has an unmatched '(' to close.
            if (closed < opened) {
                brackets.append(')')
                extend(opened, closed + 1)
                brackets.deleteCharAt(brackets.length - 1)
            }
        }

        extend(0, 0)
        return result
    }
}

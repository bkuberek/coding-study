class Solution {
    fun checkValidString(s: String): Boolean {
        val opens = ArrayDeque<Int>() // positions of unmatched "("
        val stars = ArrayDeque<Int>() // positions of unused "*"
        for ((position, c) in s.withIndex()) {
            when {
                c == '(' -> opens.addLast(position)
                c == '*' -> stars.addLast(position)
                opens.isNotEmpty() -> opens.removeLast() // prefer a real "(", keep wildcards
                stars.isNotEmpty() -> stars.removeLast()
                else -> return false
            }
        }
        // Every remaining "(" needs a later "*" to act as its ")".
        while (opens.isNotEmpty() && stars.isNotEmpty()) {
            if (opens.removeLast() > stars.removeLast()) return false
        }
        return opens.isEmpty()
    }
}

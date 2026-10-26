class Solution {
    fun minRemoveToMakeValid(s: String): String {
        val deleted = BooleanArray(s.length)
        val openPositions = ArrayDeque<Int>()
        for ((position, character) in s.withIndex()) {
            if (character == '(') {
                openPositions.addLast(position)
            } else if (character == ')') {
                if (openPositions.isNotEmpty()) {
                    openPositions.removeLast() // matches the most recent unmatched opener
                } else {
                    deleted[position] = true // nothing open: this closer can never match
                }
            }
        }
        for (position in openPositions) {
            deleted[position] = true // openers that were never closed
        }
        return s.filterIndexed { position, _ -> !deleted[position] }
    }
}

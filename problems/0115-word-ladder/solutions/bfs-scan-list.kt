private fun oneApart(first: String, second: String): Boolean {
    var differences = 0
    for (i in first.indices) {
        if (first[i] != second[i] && ++differences > 1) return false
    }
    return differences == 1
}

class Solution {
    fun ladderLength(beginWord: String, endWord: String, wordList: Array<String>): Int {
        if (endWord !in wordList) return 0
        var unvisited = wordList.filter { it != beginWord }
        var level = listOf(beginWord)
        var words = 1
        while (level.isNotEmpty()) {
            if (endWord in level) return words
            // Compare against every word not reached yet; the neighbors leave the list.
            val next = mutableListOf<String>()
            for (word in level) {
                val (neighbors, remaining) = unvisited.partition { oneApart(word, it) }
                next.addAll(neighbors)
                unvisited = remaining
            }
            level = next
            words++
        }
        return 0
    }
}

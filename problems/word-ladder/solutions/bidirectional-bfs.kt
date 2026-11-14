class Solution {
    fun ladderLength(beginWord: String, endWord: String, wordList: Array<String>): Int {
        val available = wordList.toHashSet()
        if (endWord !in available) return 0
        available.remove(beginWord)
        available.remove(endWord)
        // Two frontiers grow toward each other; words counts the ladder length covered so far.
        var near = hashSetOf(beginWord)
        var far = hashSetOf(endWord)
        var words = 1
        while (near.isNotEmpty() && far.isNotEmpty()) {
            if (near.size > far.size) near = far.also { far = near } // expand the smaller frontier
            words++
            val next = HashSet<String>()
            for (word in near) {
                val letters = word.toCharArray()
                for (position in letters.indices) {
                    val original = letters[position]
                    for (letter in 'a'..'z') {
                        letters[position] = letter
                        val candidate = String(letters)
                        if (candidate in far) return words
                        if (available.remove(candidate)) next.add(candidate)
                    }
                    letters[position] = original
                }
            }
            near = next
        }
        return 0
    }
}

class Solution {
    fun ladderLength(beginWord: String, endWord: String, wordList: Array<String>): Int {
        // Words still available; a word leaves the set the moment it is reached.
        val available = wordList.toHashSet()
        if (endWord !in available) return 0
        available.remove(beginWord)
        val queue = ArrayDeque(listOf(beginWord))
        var words = 1
        while (queue.isNotEmpty()) {
            repeat(queue.size) {
                val word = queue.removeFirst()
                if (word == endWord) return words
                val letters = word.toCharArray()
                for (position in letters.indices) {
                    val original = letters[position]
                    for (letter in 'a'..'z') {
                        letters[position] = letter
                        val candidate = String(letters)
                        if (available.remove(candidate)) queue.addLast(candidate)
                    }
                    letters[position] = original
                }
            }
            words++
        }
        return 0
    }
}

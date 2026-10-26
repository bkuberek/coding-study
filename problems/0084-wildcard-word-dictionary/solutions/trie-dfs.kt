class WordDictionary {
    private class Node {
        val children = arrayOfNulls<Node>(26)
        var isWord = false
    }

    private val root = Node()

    fun addWord(word: String) {
        var node = root
        for (letter in word) {
            val index = letter - 'a'
            node = node.children[index] ?: Node().also { node.children[index] = it }
        }
        node.isWord = true
    }

    fun search(word: String): Boolean = matchesFrom(root, word, 0)

    /** Does some stored word continue from [start] the way word[position..] says? */
    private fun matchesFrom(start: Node, word: String, position: Int): Boolean {
        var node = start
        for (at in position until word.length) {
            if (word[at] == '.') {
                return node.children.any { child -> child != null && matchesFrom(child, word, at + 1) }
            }
            node = node.children[word[at] - 'a'] ?: return false
        }
        return node.isWord
    }
}

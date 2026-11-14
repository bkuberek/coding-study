class Trie {
    private class Node {
        val children = arrayOfNulls<Node>(26)
        var isWord = false
    }

    private val root = Node()

    fun insert(word: String) {
        var node = root
        for (letter in word) {
            val index = letter - 'a'
            node = node.children[index] ?: Node().also { node.children[index] = it }
        }
        node.isWord = true
    }

    fun search(word: String): Boolean = walk(word)?.isWord == true

    fun startsWith(prefix: String): Boolean = walk(prefix) != null

    /** The node at the end of the path spelled by [text], or null if the path breaks off. */
    private fun walk(text: String): Node? {
        var node: Node? = root
        for (letter in text) {
            node = node?.children?.get(letter - 'a') ?: return null
        }
        return node
    }
}

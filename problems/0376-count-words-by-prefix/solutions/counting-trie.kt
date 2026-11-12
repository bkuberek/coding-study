private class Node {
    val children = arrayOfNulls<Node>(26)
    var passing = 0 // how many words go through this node
}

class Solution {
    fun countByPrefix(words: Array<String>, prefixes: Array<String>): IntArray {
        val root = Node()
        for (word in words) {
            var node = root
            for (letter in word) {
                val slot = letter - 'a'
                val child = node.children[slot] ?: Node().also { node.children[slot] = it }
                child.passing++
                node = child
            }
        }

        return IntArray(prefixes.size) { i ->
            var node: Node? = root
            for (letter in prefixes[i]) {
                node = node?.children?.get(letter - 'a')
            }
            // A broken path leaves null: no word begins with this prefix.
            node?.passing ?: 0
        }
    }
}

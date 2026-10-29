class Solution {
    private class TrieNode {
        val children = arrayOfNulls<TrieNode>(26)
        var end = false // a root ends at this node
    }

    fun replaceWords(dictionary: Array<String>, sentence: String): String {
        val trie = TrieNode()
        for (root in dictionary) {
            var node = trie
            for (letter in root) {
                val index = letter - 'a'
                node = node.children[index] ?: TrieNode().also { node.children[index] = it }
            }
            node.end = true
        }
        return sentence.split(' ').joinToString(" ") { shorten(trie, it) }
    }

    private fun shorten(trie: TrieNode, word: String): String {
        var node = trie
        for ((length, letter) in word.withIndex()) {
            if (node.end) return word.substring(0, length)
            node = node.children[letter - 'a'] ?: return word
        }
        return word
    }
}

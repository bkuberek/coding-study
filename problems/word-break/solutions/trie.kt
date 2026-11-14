private class TrieNode {
    val children = arrayOfNulls<TrieNode>(26)
    var endsWord = false
}

class Solution {
    fun wordBreak(s: String, wordDict: Array<String>): Boolean {
        val root = TrieNode()
        for (word in wordDict) {
            var node = root
            for (letter in word) {
                val index = letter - 'a'
                node = node.children[index] ?: TrieNode().also { node.children[index] = it }
            }
            node.endsWord = true
        }

        // reachable[i] is true when the prefix s[0 until i] can be split into dictionary words.
        val reachable = BooleanArray(s.length + 1)
        reachable[0] = true
        for (start in s.indices) {
            if (!reachable[start]) continue
            var node = root
            for (position in start until s.length) {
                node = node.children[s[position] - 'a'] ?: break
                if (node.endsWord) reachable[position + 1] = true
            }
        }
        return reachable[s.length]
    }
}

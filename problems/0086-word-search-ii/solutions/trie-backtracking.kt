class Solution {
    private class Node {
        val children = arrayOfNulls<Node>(26)
        var word: String? = null
    }

    fun findWords(board: Array<CharArray>, words: Array<String>): List<String> {
        val root = Node()
        for (word in words) {
            var node = root
            for (letter in word) {
                val index = letter - 'a'
                node = node.children[index] ?: Node().also { node.children[index] = it }
            }
            node.word = word
        }
        val found = mutableListOf<String>()

        fun explore(row: Int, col: Int, parent: Node) {
            val letter = board[row][col]
            if (letter == USED) return
            val node = parent.children[letter - 'a'] ?: return
            node.word?.let {
                found.add(it)
                node.word = null
            }
            board[row][col] = USED
            for ((dr, dc) in STEPS) {
                val r = row + dr
                val c = col + dc
                if (r in board.indices && c in board[0].indices) explore(r, c, node)
            }
            board[row][col] = letter
        }

        for (row in board.indices) {
            for (col in board[0].indices) explore(row, col, root)
        }
        return found
    }

    private companion object {
        const val USED = '#'
        val STEPS = listOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)
    }
}

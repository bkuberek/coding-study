class Solution {
    private class Node {
        val children = arrayOfNulls<Node>(26)
        val smallest = ArrayList<String>(SHOWN)
    }

    fun suggestedProducts(products: Array<String>, searchWord: String): List<List<String>> {
        val root = Node()
        // Inserting in sorted order means each node's first three products are its smallest.
        for (product in products.sorted()) {
            var node = root
            for (letter in product) {
                val index = letter - 'a'
                node = node.children[index] ?: Node().also { node.children[index] = it }
                if (node.smallest.size < SHOWN) node.smallest.add(product)
            }
        }
        var node: Node? = root
        return searchWord.map { letter ->
            node = node?.children?.get(letter - 'a')
            node?.smallest?.toList() ?: emptyList()
        }
    }

    private companion object {
        const val SHOWN = 3
    }
}

import cs.support.*

class Solution {
    fun serializeDeserialize(root: TreeNode?): TreeNode? = deserialize(serialize(root))

    fun serialize(root: TreeNode?): String {
        val tokens = ArrayList<String>()

        fun write(node: TreeNode?) {
            if (node == null) {
                tokens.add(MISSING)
                return
            }
            tokens.add(node.`val`.toString())
            write(node.left)
            write(node.right)
        }

        write(root)
        return tokens.joinToString(SEPARATOR)
    }

    fun deserialize(data: String): TreeNode? {
        val tokens = data.split(SEPARATOR).iterator()

        fun read(): TreeNode? {
            val token = tokens.next()
            if (token == MISSING) return null
            return TreeNode(token.toInt()).apply {
                left = read()
                right = read()
            }
        }

        return read()
    }

    private companion object {
        const val MISSING = "#"
        const val SEPARATOR = ","
    }
}

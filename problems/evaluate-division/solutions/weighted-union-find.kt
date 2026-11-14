class Solution {
    fun calcEquation(equations: Array<Array<String>>, values: DoubleArray, queries: Array<Array<String>>): DoubleArray {
        // parent[x] is x's parent; weight[x] is the value of x / parent[x].
        val parent = HashMap<String, String>()
        val weight = HashMap<String, Double>()

        // Returns the root of name; afterwards parent[name] is the root and weight[name] is name / root.
        fun find(name: String): String {
            val path = mutableListOf<String>()
            var node = name
            while (parent.getValue(node) != node) {
                path.add(node)
                node = parent.getValue(node)
            }
            val root = node
            for (current in path.asReversed()) {
                val up = parent.getValue(current)
                if (up != root) {
                    weight[current] = weight.getValue(current) * weight.getValue(up)
                    parent[current] = root
                }
            }
            return root
        }

        for ((i, equation) in equations.withIndex()) {
            val (a, b) = equation
            for (name in equation) {
                if (name !in parent) {
                    parent[name] = name
                    weight[name] = 1.0
                }
            }
            val rootA = find(a)
            val rootB = find(b)
            if (rootA != rootB) {
                // Hang rootA under rootB: rootA / rootB = (a / b) * (b / rootB) / (a / rootA).
                parent[rootA] = rootB
                weight[rootA] = values[i] * weight.getValue(b) / weight.getValue(a)
            }
        }

        return DoubleArray(queries.size) { j ->
            val (c, d) = queries[j]
            if (c !in parent || d !in parent || find(c) != find(d)) {
                -1.0
            } else {
                weight.getValue(c) / weight.getValue(d)
            }
        }
    }
}

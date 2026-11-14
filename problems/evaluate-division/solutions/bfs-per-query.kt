class Solution {
    fun calcEquation(equations: Array<Array<String>>, values: DoubleArray, queries: Array<Array<String>>): DoubleArray {
        // graph[a][b] is the value of a / b, stored in both directions.
        val graph = HashMap<String, HashMap<String, Double>>()
        for ((i, equation) in equations.withIndex()) {
            val (a, b) = equation
            graph.getOrPut(a) { HashMap() }[b] = values[i]
            graph.getOrPut(b) { HashMap() }[a] = 1.0 / values[i]
        }

        fun ratio(source: String, target: String): Double {
            if (source !in graph || target !in graph) return -1.0
            // product[x] is the value of source / x along the path that reached x.
            val product = hashMapOf(source to 1.0)
            val queue = ArrayDeque(listOf(source))
            while (queue.isNotEmpty()) {
                val node = queue.removeFirst()
                if (node == target) return product.getValue(node)
                for ((neighbor, value) in graph.getValue(node)) {
                    if (neighbor !in product) {
                        product[neighbor] = product.getValue(node) * value
                        queue.addLast(neighbor)
                    }
                }
            }
            return -1.0
        }

        return DoubleArray(queries.size) { ratio(queries[it][0], queries[it][1]) }
    }
}

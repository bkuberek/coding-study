class Solution {
    fun hasPath(n: Int, edges: Array<IntArray>, source: Int, target: Int): Boolean {
        val reached = BooleanArray(n)
        reached[source] = true
        var changed = true
        while (changed && !reached[target]) {
            changed = false
            for ((a, b) in edges) {
                // A connection with exactly one reached end brings the other end in.
                if (reached[a] != reached[b]) {
                    reached[a] = true
                    reached[b] = true
                    changed = true
                }
            }
        }
        return reached[target]
    }
}

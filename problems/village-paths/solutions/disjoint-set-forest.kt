class VillageMap(villages: Int) {
    private val parent = IntArray(villages) { it } // parent[v] == v marks the leader of a group
    private val size = IntArray(villages) { 1 } // size[r]: villages in the group led by r
    private var groups = villages

    private fun leader(start: Int): Int {
        var root = start
        while (parent[root] != root) root = parent[root]
        // Path compression: send everything passed on the way straight to the leader.
        var village = start
        while (parent[village] != root) {
            val next = parent[village]
            parent[village] = root
            village = next
        }
        return root
    }

    fun addPath(a: Int, b: Int): Boolean {
        var leaderA = leader(a)
        var leaderB = leader(b)
        if (leaderA == leaderB) return false
        if (size[leaderA] < size[leaderB]) leaderA = leaderB.also { leaderB = leaderA }
        parent[leaderB] = leaderA // union by size: the smaller group joins the larger
        size[leaderA] += size[leaderB]
        groups--
        return true
    }

    fun canReach(a: Int, b: Int): Boolean = leader(a) == leader(b)

    fun groupSize(village: Int): Int = size[leader(village)]

    fun groupCount(): Int = groups
}

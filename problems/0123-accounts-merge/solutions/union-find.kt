private class DisjointSets(count: Int) {
    private val parent = IntArray(count) { it }
    private val size = IntArray(count) { 1 } // size[r]: number of accounts in the tree rooted at r

    fun find(start: Int): Int {
        var root = start
        while (parent[root] != root) root = parent[root]
        var x = start
        while (parent[x] != root) { // path compression: point the whole path at the root
            val next = parent[x]
            parent[x] = root
            x = next
        }
        return root
    }

    fun union(a: Int, b: Int) {
        var rootA = find(a)
        var rootB = find(b)
        if (rootA == rootB) return
        if (size[rootA] < size[rootB]) rootA = rootB.also { rootB = rootA }
        parent[rootB] = rootA // union by size: the smaller tree goes under the larger
        size[rootA] += size[rootB]
    }
}

class Solution {
    fun accountsMerge(accounts: List<List<String>>): List<List<String>> {
        val sets = DisjointSets(accounts.size)
        val firstOwner = HashMap<String, Int>() // address -> first account that listed it
        accounts.forEachIndexed { i, account ->
            for (address in account.drop(1)) {
                firstOwner.putIfAbsent(address, i)?.let { owner -> sets.union(owner, i) }
            }
        }
        return accounts.indices
            .groupBy(sets::find)
            .map { (root, members) ->
                listOf(accounts[root][0]) + members.flatMap { accounts[it].drop(1) }.distinct().sorted()
            }
    }
}

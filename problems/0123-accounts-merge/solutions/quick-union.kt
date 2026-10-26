class Solution {
    fun accountsMerge(accounts: List<List<String>>): List<List<String>> {
        val parent = IntArray(accounts.size) { it } // parent[x] == x marks a root

        fun find(start: Int): Int {
            var x = start
            while (parent[x] != x) x = parent[x]
            return x
        }

        val firstOwner = HashMap<String, Int>() // address -> first account that listed it
        accounts.forEachIndexed { i, account ->
            for (address in account.drop(1)) {
                val owner = firstOwner.putIfAbsent(address, i) ?: continue
                val rootOwner = find(owner)
                val rootHere = find(i)
                if (rootOwner != rootHere) parent[rootOwner] = rootHere // no balancing: chains can grow
            }
        }
        return accounts.indices
            .groupBy(::find)
            .map { (root, members) ->
                listOf(accounts[root][0]) + members.flatMap { accounts[it].drop(1) }.distinct().sorted()
            }
    }
}

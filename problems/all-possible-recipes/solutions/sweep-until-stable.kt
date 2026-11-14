class Solution {
    fun findAllRecipes(recipes: Array<String>, ingredients: List<List<String>>, supplies: Array<String>): List<String> {
        val available = supplies.toHashSet()
        val prepared = mutableListOf<String>()
        var pending = recipes.indices.toList()
        do {
            val (ready, stillPending) = pending.partition { available.containsAll(ingredients[it]) }
            for (i in ready) {
                available.add(recipes[i])
                prepared.add(recipes[i])
            }
            pending = stillPending
        } while (ready.isNotEmpty())
        return prepared
    }
}

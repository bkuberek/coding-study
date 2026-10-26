class Solution {
    fun findAllRecipes(recipes: Array<String>, ingredients: List<List<String>>, supplies: Array<String>): List<String> {
        val usedBy = HashMap<String, MutableList<Int>>()
        ingredients.forEachIndexed { i, items ->
            for (item in items) usedBy.getOrPut(item) { mutableListOf() }.add(i)
        }
        val missing = IntArray(recipes.size) { ingredients[it].size } // ingredients each recipe still lacks
        val available = ArrayDeque(supplies.asList())
        val prepared = mutableListOf<String>()
        while (available.isNotEmpty()) {
            for (i in usedBy[available.removeFirst()].orEmpty()) {
                if (--missing[i] == 0) {
                    prepared.add(recipes[i])
                    available.addLast(recipes[i])
                }
            }
        }
        return prepared
    }
}

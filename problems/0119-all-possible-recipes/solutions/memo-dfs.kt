private enum class Verdict { ON_PATH, PREPARABLE, IMPOSSIBLE }

class Solution {
    fun findAllRecipes(recipes: Array<String>, ingredients: List<List<String>>, supplies: Array<String>): List<String> {
        val needs = recipes.zip(ingredients).toMap()
        val stocked = supplies.toHashSet()
        val verdict = HashMap<String, Verdict>()

        fun canPrepare(item: String): Boolean {
            if (item in stocked) return true
            val items = needs[item] ?: return false // neither a supply nor a recipe
            // ON_PATH means the ingredients loop back to this recipe.
            verdict[item]?.let { return it == Verdict.PREPARABLE }
            verdict[item] = Verdict.ON_PATH
            val result = items.all { canPrepare(it) }
            verdict[item] = if (result) Verdict.PREPARABLE else Verdict.IMPOSSIBLE
            return result
        }

        return recipes.filter { canPrepare(it) }
    }
}

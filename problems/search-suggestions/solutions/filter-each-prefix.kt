class Solution {
    fun suggestedProducts(products: Array<String>, searchWord: String): List<List<String>> =
        (1..searchWord.length).map { typed ->
            val prefix = searchWord.substring(0, typed)
            products.filter { it.startsWith(prefix) }.sorted().take(3)
        }
}

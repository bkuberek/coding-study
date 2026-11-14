class WordDictionary {
    private val byLength = HashMap<Int, MutableSet<String>>()

    fun addWord(word: String) {
        byLength.getOrPut(word.length) { HashSet() }.add(word)
    }

    fun search(word: String): Boolean {
        val candidates = byLength[word.length] ?: return false
        if ('.' !in word) return word in candidates
        return candidates.any { candidate -> word.indices.all { word[it] == '.' || word[it] == candidate[it] } }
    }
}

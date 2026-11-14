class Trie {
    private val words = HashSet<String>()

    fun insert(word: String) {
        words.add(word)
    }

    fun search(word: String): Boolean = word in words

    fun startsWith(prefix: String): Boolean = words.any { it.startsWith(prefix) }
}

class Solution {
    fun countByPrefix(words: Array<String>, prefixes: Array<String>): IntArray =
        IntArray(prefixes.size) { i -> words.count { it.startsWith(prefixes[i]) } }
}

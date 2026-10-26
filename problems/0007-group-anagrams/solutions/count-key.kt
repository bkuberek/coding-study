private const val ALPHABET_SIZE = 26

class Solution {
    fun groupAnagrams(strs: Array<String>): List<List<String>> {
        val groups = HashMap<List<Int>, MutableList<String>>()
        for (word in strs) {
            val counts = IntArray(ALPHABET_SIZE)
            for (letter in word) {
                counts[letter - 'a']++
            }
            // IntArray compares by reference; List<Int> has structural equals and hashCode.
            groups.getOrPut(counts.toList()) { mutableListOf() }.add(word)
        }
        return groups.values.toList()
    }
}

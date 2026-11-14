class Solution {
    fun groupAnagrams(strs: Array<String>): List<List<String>> {
        val keys = mutableListOf<String>()
        val groups = mutableListOf<MutableList<String>>()
        for (word in strs) {
            val key = String(word.toCharArray().sortedArray())
            val index = keys.indexOf(key)
            if (index == -1) {
                keys.add(key)
                groups.add(mutableListOf(word))
            } else {
                groups[index].add(word)
            }
        }
        return groups
    }
}

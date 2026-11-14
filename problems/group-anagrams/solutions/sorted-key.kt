class Solution {
    fun groupAnagrams(strs: Array<String>): List<List<String>> =
        strs.groupBy { word -> String(word.toCharArray().sortedArray()) }.values.toList()
}

class Solution {
    fun isAnagram(s: String, t: String): Boolean =
        s.length == t.length && s.toCharArray().sortedArray().contentEquals(t.toCharArray().sortedArray())
}

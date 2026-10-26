class Solution {
    fun checkInclusion(pattern: String, text: String): Boolean {
        val width = pattern.length
        val target = pattern.toCharArray().apply { sort() }
        return (0..text.length - width).any { start ->
            text.substring(start, start + width).toCharArray().apply { sort() }.contentEquals(target)
        }
    }
}

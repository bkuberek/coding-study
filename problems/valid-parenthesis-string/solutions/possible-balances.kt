class Solution {
    fun checkValidString(s: String): Boolean {
        val n = s.length
        // possible[k] is true when some choice of wildcards gives the prefix an open count of k.
        var possible = BooleanArray(n + 2)
        var following = BooleanArray(n + 2)
        possible[0] = true
        for (c in s) {
            following.fill(false)
            var any = false
            for (open in 0..n) {
                if (!possible[open]) continue
                if (c != ')') following[open + 1] = true // "(" or a wildcard as "("
                if (c != '(' && open > 0) following[open - 1] = true // ")" or a wildcard as ")"
                if (c == '*') following[open] = true // a wildcard as nothing
                any = true
            }
            if (!any) return false
            possible = following.also { following = possible }
        }
        return possible[0]
    }
}

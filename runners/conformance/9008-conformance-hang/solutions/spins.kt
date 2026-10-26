class Solution {
    fun waitFor(value: Int): Int {
        while (value < 0) {
            Thread.onSpinWait()
        }
        return value
    }
}

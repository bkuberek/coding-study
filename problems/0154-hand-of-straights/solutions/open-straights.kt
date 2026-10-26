import java.util.ArrayDeque
import java.util.TreeMap

class Solution {
    fun isNStraightHand(hand: IntArray, groupSize: Int): Boolean {
        if (hand.size % groupSize != 0) return false
        val counts = TreeMap<Int, Int>()
        for (card in hand) counts.merge(card, 1, Int::plus)
        var openCount = 0 // straights started but not yet complete; each needs the current value
        val opened = ArrayDeque<Int>() // straights opened at each of the last values
        var previous = -1
        for ((value, count) in counts) {
            if (openCount > 0 && value != previous + 1) return false
            if (count < openCount) return false
            val fresh = count - openCount
            opened.addLast(fresh)
            openCount += fresh
            if (opened.size == groupSize) {
                // The straights opened groupSize values ago end with this value.
                openCount -= opened.removeFirst()
            }
            previous = value
        }
        return openCount == 0
    }
}

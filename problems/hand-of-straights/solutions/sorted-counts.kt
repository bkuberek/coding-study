import java.util.TreeMap

class Solution {
    fun isNStraightHand(hand: IntArray, groupSize: Int): Boolean {
        if (hand.size % groupSize != 0) return false
        val counts = TreeMap<Int, Int>()
        for (card in hand) counts.merge(card, 1, Int::plus)
        for (value in counts.keys) {
            val starting = counts.getValue(value)
            if (starting == 0) continue
            // Every card left at the smallest remaining value starts its own straight.
            for (following in value until value + groupSize) {
                val available = counts.getOrDefault(following, 0)
                if (available < starting) return false
                counts[following] = available - starting
            }
        }
        return true
    }
}

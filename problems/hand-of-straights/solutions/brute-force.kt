class Solution {
    fun isNStraightHand(hand: IntArray, groupSize: Int): Boolean {
        if (hand.size % groupSize != 0) return false
        val cards = hand.sorted().toMutableList()
        while (cards.isNotEmpty()) {
            // The smallest card must start a straight; remove that straight card by card.
            val smallest = cards.removeAt(0)
            for (value in smallest + 1 until smallest + groupSize) {
                if (!cards.remove(value)) return false
            }
        }
        return true
    }
}

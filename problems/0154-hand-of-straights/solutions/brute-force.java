import java.util.*;

public class Solution {
    public boolean isNStraightHand(int[] hand, int groupSize) {
        if (hand.length % groupSize != 0) {
            return false;
        }
        List<Integer> cards = new ArrayList<>();
        for (int card : hand) {
            cards.add(card);
        }
        Collections.sort(cards);
        while (!cards.isEmpty()) {
            // The smallest card must start a straight; remove that straight card by card.
            int smallest = cards.remove(0);
            for (int value = smallest + 1; value < smallest + groupSize; value++) {
                // remove(Object) removes one card with this value; remove(int) would take an index.
                if (!cards.remove(Integer.valueOf(value))) {
                    return false;
                }
            }
        }
        return true;
    }
}

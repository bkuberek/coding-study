import java.util.*;

public class Solution {
    public boolean isNStraightHand(int[] hand, int groupSize) {
        if (hand.length % groupSize != 0) {
            return false;
        }
        TreeMap<Integer, Integer> counts = new TreeMap<>();
        for (int card : hand) {
            counts.merge(card, 1, Integer::sum);
        }
        for (int value : counts.keySet()) {
            int starting = counts.get(value);
            if (starting == 0) {
                continue;
            }
            // Every card left at the smallest remaining value starts its own straight.
            for (int following = value; following < value + groupSize; following++) {
                int available = counts.getOrDefault(following, 0);
                if (available < starting) {
                    return false;
                }
                counts.put(following, available - starting);
            }
        }
        return true;
    }
}

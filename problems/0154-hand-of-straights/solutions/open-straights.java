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
        int openCount = 0; // straights started but not yet complete; each needs the current value
        ArrayDeque<Integer> opened = new ArrayDeque<>(); // straights opened at the last values
        int previous = -1;
        for (Map.Entry<Integer, Integer> entry : counts.entrySet()) {
            int value = entry.getKey();
            if (openCount > 0 && value != previous + 1) {
                return false; // an open straight needs previous + 1, which is missing
            }
            if (entry.getValue() < openCount) {
                return false;
            }
            int fresh = entry.getValue() - openCount;
            opened.addLast(fresh);
            openCount += fresh;
            if (opened.size() == groupSize) {
                // The straights opened groupSize values ago end with this value.
                openCount -= opened.pollFirst();
            }
            previous = value;
        }
        return openCount == 0;
    }
}

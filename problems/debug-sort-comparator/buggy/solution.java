// Debug: Leaderboard Comparator. Some tests fail: find the bug and fix it.
import java.util.*;

public class Solution {
    private static final int SCORE_EPSILON = 1;

    public String[] rankPlayers(String[] names, int[] scores) {
        Integer[] order = new Integer[names.length];
        for (int i = 0; i < order.length; i++) {
            order[i] = i;
        }
        Arrays.sort(order, (a, b) -> {
            if (Math.abs(scores[a] - scores[b]) <= SCORE_EPSILON) {
                return names[a].compareTo(names[b]);
            }
            return scores[b] - scores[a];
        });
        String[] ranked = new String[order.length];
        for (int i = 0; i < order.length; i++) {
            ranked[i] = names[order[i]];
        }
        return ranked;
    }
}

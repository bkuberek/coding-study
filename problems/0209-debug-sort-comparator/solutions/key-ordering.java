import java.util.*;

public class Solution {
    public String[] rankPlayers(String[] names, int[] scores) {
        Integer[] order = new Integer[names.length];
        for (int i = 0; i < order.length; i++) {
            order[i] = i;
        }
        Comparator<Integer> byScoreDescending = (a, b) -> Integer.compare(scores[b], scores[a]);
        Arrays.sort(order, byScoreDescending.thenComparing(i -> names[i]));
        String[] ranked = new String[order.length];
        for (int i = 0; i < order.length; i++) {
            ranked[i] = names[order[i]];
        }
        return ranked;
    }
}

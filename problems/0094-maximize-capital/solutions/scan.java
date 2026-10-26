public class Solution {
    public int findMaximizedCapital(int k, int w, int[] profits, int[] capital) {
        boolean[] used = new boolean[profits.length];
        for (int round = 0; round < k; round++) {
            int best = -1;
            for (int index = 0; index < profits.length; index++) {
                if (!used[index] && capital[index] <= w && (best < 0 || profits[index] > profits[best])) {
                    best = index;
                }
            }
            if (best < 0) {
                break; // nothing affordable now, and capital cannot grow any more
            }
            used[best] = true;
            w += profits[best];
        }
        return w;
    }
}

public class Solution {
    public int totalFruit(int[] fruits) {
        int best = 0;
        int window = 0;
        int last = -1;
        int beforeLast = -1;
        int lastRun = 0;
        for (int fruit : fruits) {
            window = fruit == last || fruit == beforeLast ? window + 1 : lastRun + 1;
            if (fruit == last) {
                lastRun++;
            } else {
                beforeLast = last;
                last = fruit;
                lastRun = 1;
            }
            best = Math.max(best, window);
        }
        return best;
    }
}

import java.util.*;

public class Solution {
    public int totalFruit(int[] fruits) {
        Map<Integer, Integer> inWindow = new HashMap<>();
        int left = 0;
        int best = 0;
        for (int right = 0; right < fruits.length; right++) {
            inWindow.merge(fruits[right], 1, Integer::sum);
            while (inWindow.size() > 2) {
                int leaving = fruits[left++];
                if (inWindow.merge(leaving, -1, Integer::sum) == 0) {
                    inWindow.remove(leaving);
                }
            }
            best = Math.max(best, right - left + 1);
        }
        return best;
    }
}

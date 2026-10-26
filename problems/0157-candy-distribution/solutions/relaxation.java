import java.util.*;

public class Solution {
    public int candy(int[] ratings) {
        int n = ratings.length;
        int[] candies = new int[n];
        Arrays.fill(candies, 1);
        boolean changed = true;
        while (changed) {
            // Raise any child who does not have more than a lower-rated neighbor; repeat until
            // no rule is violated. Counts only grow, and each raise is the least that fixes it.
            changed = false;
            for (int i = 0; i < n; i++) {
                if (i > 0 && ratings[i] > ratings[i - 1] && candies[i] <= candies[i - 1]) {
                    candies[i] = candies[i - 1] + 1;
                    changed = true;
                }
                if (i < n - 1 && ratings[i] > ratings[i + 1] && candies[i] <= candies[i + 1]) {
                    candies[i] = candies[i + 1] + 1;
                    changed = true;
                }
            }
        }
        return Arrays.stream(candies).sum();
    }
}

import java.util.*;

public class Solution {
    public int rob(int[] nums) {
        // Before each house: withoutLast and withLast are the best totals for the prefixes
        // that end two houses back and one house back.
        int withoutLast = 0;
        int withLast = 0;
        for (int cash : nums) {
            int current = Math.max(withLast, withoutLast + cash);
            withoutLast = withLast;
            withLast = current;
        }
        return withLast;
    }
}

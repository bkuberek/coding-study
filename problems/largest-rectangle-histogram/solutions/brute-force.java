import java.util.*;

public class Solution {
    public int largestRectangleArea(int[] heights) {
        int best = 0;
        for (int left = 0; left < heights.length; left++) {
            // The tallest rectangle spanning bars left..right is as high as the lowest of them.
            int lowest = heights[left];
            for (int right = left; right < heights.length; right++) {
                lowest = Math.min(lowest, heights[right]);
                best = Math.max(best, lowest * (right - left + 1));
            }
        }
        return best;
    }
}

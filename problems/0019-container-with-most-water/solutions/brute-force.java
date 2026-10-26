public class Solution {
    public int maxArea(int[] height) {
        int best = 0;
        for (int left = 0; left < height.length - 1; left++) {
            for (int right = left + 1; right < height.length; right++) {
                best = Math.max(best, (right - left) * Math.min(height[left], height[right]));
            }
        }
        return best;
    }
}

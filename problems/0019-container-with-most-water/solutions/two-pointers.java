public class Solution {
    public int maxArea(int[] height) {
        int left = 0;
        int right = height.length - 1;
        int best = 0;
        while (left < right) {
            int width = right - left;
            if (height[left] < height[right]) {
                best = Math.max(best, width * height[left]);
                left++;
            } else {
                best = Math.max(best, width * height[right]);
                right--;
            }
        }
        return best;
    }
}

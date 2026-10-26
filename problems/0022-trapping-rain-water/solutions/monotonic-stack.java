import java.util.*;

public class Solution {
    public int trap(int[] height) {
        int water = 0;
        Deque<Integer> falling = new ArrayDeque<>();
        for (int right = 0; right < height.length; right++) {
            while (!falling.isEmpty() && height[falling.peek()] < height[right]) {
                int bottom = height[falling.pop()];
                if (falling.isEmpty()) {
                    break;
                }
                int left = falling.peek();
                int level = Math.min(height[left], height[right]);
                water += (right - left - 1) * (level - bottom);
            }
            falling.push(right);
        }
        return water;
    }
}

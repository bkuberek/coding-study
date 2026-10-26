import java.util.*;

public class Solution {
    public boolean canJump(int[] nums) {
        int goal = nums.length - 1; // the leftmost index known to reach the last index
        for (int i = nums.length - 2; i >= 0; i--) {
            if (i + nums[i] >= goal) {
                goal = i;
            }
        }
        return goal == 0;
    }
}

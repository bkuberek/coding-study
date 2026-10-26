import java.util.*;

public class Solution {
    public void sortColors(int[] nums) {
        int[] counts = new int[3];
        for (int color : nums) {
            counts[color]++;
        }
        Arrays.fill(nums, 0, counts[0], 0);
        Arrays.fill(nums, counts[0], counts[0] + counts[1], 1);
        Arrays.fill(nums, counts[0] + counts[1], nums.length, 2);
    }
}

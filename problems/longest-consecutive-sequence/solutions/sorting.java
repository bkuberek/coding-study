import java.util.*;

public class Solution {
    public int longestConsecutive(int[] nums) {
        if (nums.length == 0) {
            return 0;
        }
        int[] ordered = nums.clone();
        Arrays.sort(ordered);
        int longest = 1;
        int current = 1;
        for (int i = 1; i < ordered.length; i++) {
            if (ordered[i] == ordered[i - 1]) {
                continue;
            }
            current = ordered[i] == ordered[i - 1] + 1 ? current + 1 : 1;
            longest = Math.max(longest, current);
        }
        return longest;
    }
}

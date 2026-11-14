import java.util.*;

public class Solution {
    public int longestConsecutive(int[] nums) {
        Set<Integer> present = new HashSet<>();
        for (int value : nums) {
            present.add(value);
        }
        int longest = 0;
        for (int value : present) {
            if (present.contains(value - 1)) {
                continue;
            }
            int end = value + 1;
            while (present.contains(end)) {
                end++;
            }
            longest = Math.max(longest, end - value);
        }
        return longest;
    }
}

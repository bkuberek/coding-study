import java.util.*;

public class Solution {
    public int firstMissingPositive(int[] nums) {
        Set<Integer> present = new HashSet<>();
        for (int value : nums) {
            present.add(value);
        }
        // The answer is at most nums.length + 1, so this loop runs at most n + 1 times.
        int candidate = 1;
        while (present.contains(candidate)) {
            candidate++;
        }
        return candidate;
    }
}

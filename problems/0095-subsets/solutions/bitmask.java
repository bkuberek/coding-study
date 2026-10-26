import java.util.*;

public class Solution {
    public List<List<Integer>> subsets(int[] nums) {
        int count = 1 << nums.length;
        List<List<Integer>> result = new ArrayList<>(count);
        // Bit i of mask says whether nums[i] belongs to the subset that mask encodes.
        for (int mask = 0; mask < count; mask++) {
            List<Integer> subset = new ArrayList<>();
            for (int i = 0; i < nums.length; i++) {
                if ((mask >> i & 1) == 1) {
                    subset.add(nums[i]);
                }
            }
            result.add(subset);
        }
        return result;
    }
}

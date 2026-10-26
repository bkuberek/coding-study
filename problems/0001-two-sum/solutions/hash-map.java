import java.util.*;

public class Solution {
    public int[] twoSum(int[] nums, int target) {
        Map<Integer, Integer> indexByValue = new HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            Integer partner = indexByValue.get(target - nums[i]);
            if (partner != null) {
                return new int[] {partner, i};
            }
            indexByValue.put(nums[i], i);
        }
        return new int[0];
    }
}

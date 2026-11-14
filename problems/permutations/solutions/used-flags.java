import java.util.*;

public class Solution {
    public List<List<Integer>> permute(int[] nums) {
        List<List<Integer>> result = new ArrayList<>();
        fillNextSlot(nums, new boolean[nums.length], new ArrayList<>(), result);
        return result;
    }

    private void fillNextSlot(int[] nums, boolean[] used, List<Integer> ordering, List<List<Integer>> result) {
        if (ordering.size() == nums.length) {
            result.add(new ArrayList<>(ordering));
            return;
        }
        for (int i = 0; i < nums.length; i++) {
            if (used[i]) {
                continue;
            }
            used[i] = true;
            ordering.add(nums[i]);
            fillNextSlot(nums, used, ordering, result);
            ordering.remove(ordering.size() - 1);
            used[i] = false;
        }
    }
}

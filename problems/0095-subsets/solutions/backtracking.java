import java.util.*;

public class Solution {
    public List<List<Integer>> subsets(int[] nums) {
        List<List<Integer>> result = new ArrayList<>();
        explore(nums, 0, new ArrayList<>(), result);
        return result;
    }

    private void explore(int[] nums, int index, List<Integer> chosen, List<List<Integer>> result) {
        if (index == nums.length) {
            result.add(new ArrayList<>(chosen));
            return;
        }
        chosen.add(nums[index]);
        explore(nums, index + 1, chosen, result);
        chosen.remove(chosen.size() - 1);
        explore(nums, index + 1, chosen, result);
    }
}

import java.util.*;

public class Solution {
    public List<List<Integer>> combinationSum(int[] candidates, int target) {
        int[] ordered = candidates.clone();
        Arrays.sort(ordered);
        List<List<Integer>> result = new ArrayList<>();
        extend(ordered, 0, target, new ArrayList<>(), result);
        return result;
    }

    // Values are added in non-decreasing order, so each combination is built once.
    private void extend(int[] ordered, int start, int remaining, List<Integer> chosen,
                        List<List<Integer>> result) {
        if (remaining == 0) {
            result.add(new ArrayList<>(chosen));
            return;
        }
        for (int i = start; i < ordered.length && ordered[i] <= remaining; i++) {
            chosen.add(ordered[i]);
            extend(ordered, i, remaining - ordered[i], chosen, result);
            chosen.remove(chosen.size() - 1);
        }
    }
}

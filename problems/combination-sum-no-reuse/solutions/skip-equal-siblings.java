import java.util.*;

public class Solution {
    public List<List<Integer>> combinationSum2(int[] candidates, int target) {
        int[] ordered = candidates.clone();
        Arrays.sort(ordered);
        List<List<Integer>> result = new ArrayList<>();
        extend(ordered, 0, target, new ArrayList<>(), result);
        return result;
    }

    private void extend(int[] ordered, int start, int remaining, List<Integer> chosen,
                        List<List<Integer>> result) {
        if (remaining == 0) {
            result.add(new ArrayList<>(chosen));
            return;
        }
        for (int i = start; i < ordered.length && ordered[i] <= remaining; i++) {
            // A second copy at the same level would rebuild the first copy's combinations.
            if (i > start && ordered[i] == ordered[i - 1]) {
                continue;
            }
            chosen.add(ordered[i]);
            extend(ordered, i + 1, remaining - ordered[i], chosen, result);
            chosen.remove(chosen.size() - 1);
        }
    }
}

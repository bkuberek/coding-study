import java.util.*;

public class Solution {
    public List<List<Integer>> combinationSum(int[] candidates, int target) {
        List<List<Integer>> result = new ArrayList<>();
        explore(candidates, 0, target, new ArrayList<>(), result);
        return result;
    }

    private void explore(int[] candidates, int index, int remaining, List<Integer> chosen,
                         List<List<Integer>> result) {
        if (remaining == 0) {
            result.add(new ArrayList<>(chosen));
            return;
        }
        if (remaining < 0 || index == candidates.length) {
            return;
        }
        // Use candidates[index] once more and stay on it, since it may repeat.
        chosen.add(candidates[index]);
        explore(candidates, index, remaining - candidates[index], chosen, result);
        chosen.remove(chosen.size() - 1);
        // Or never use it again.
        explore(candidates, index + 1, remaining, chosen, result);
    }
}

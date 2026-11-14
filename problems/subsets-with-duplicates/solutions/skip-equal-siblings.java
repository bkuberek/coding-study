import java.util.*;

public class Solution {
    public List<List<Integer>> subsetsWithDup(int[] nums) {
        int[] ordered = nums.clone();
        Arrays.sort(ordered);
        List<List<Integer>> result = new ArrayList<>();
        extend(ordered, 0, new ArrayList<>(), result);
        return result;
    }

    private void extend(int[] ordered, int start, List<Integer> chosen, List<List<Integer>> result) {
        // Every node of this recursion is a distinct subset.
        result.add(new ArrayList<>(chosen));
        for (int i = start; i < ordered.length; i++) {
            // A second copy at the same level would rebuild the first copy's subtree.
            if (i > start && ordered[i] == ordered[i - 1]) {
                continue;
            }
            chosen.add(ordered[i]);
            extend(ordered, i + 1, chosen, result);
            chosen.remove(chosen.size() - 1);
        }
    }
}

import java.util.*;

public class Solution {
    public List<List<Integer>> combinationSum2(int[] candidates, int target) {
        int[] ordered = candidates.clone();
        Arrays.sort(ordered);
        // Values taken in sorted order give each multiset one canonical list; lists hash by content.
        Set<List<Integer>> found = new HashSet<>();
        for (int mask = 0; mask < 1 << ordered.length; mask++) {
            List<Integer> chosen = new ArrayList<>();
            int sum = 0;
            for (int i = 0; i < ordered.length; i++) {
                if ((mask >> i & 1) == 1) {
                    chosen.add(ordered[i]);
                    sum += ordered[i];
                }
            }
            if (sum == target) {
                found.add(chosen);
            }
        }
        return new ArrayList<>(found);
    }
}

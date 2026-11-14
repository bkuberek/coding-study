import java.util.*;

public class Solution {
    public List<List<Integer>> findMissingAndDuplicates(int[] nums) {
        Set<Integer> seen = new HashSet<>();
        Set<Integer> repeated = new HashSet<>();
        for (int value : nums) {
            if (!seen.add(value)) {
                repeated.add(value);
            }
        }
        // Walking 1..n instead of the sets keeps both answers sorted without a sort.
        List<Integer> missing = new ArrayList<>();
        List<Integer> duplicated = new ArrayList<>();
        for (int value = 1; value <= nums.length; value++) {
            if (!seen.contains(value)) {
                missing.add(value);
            }
            if (repeated.contains(value)) {
                duplicated.add(value);
            }
        }
        return List.of(missing, duplicated);
    }
}

import java.util.*;

public class Solution {
    public List<List<Integer>> findMissingAndDuplicates(int[] nums) {
        Arrays.sort(nums);
        List<Integer> missing = new ArrayList<>();
        List<Integer> duplicated = new ArrayList<>();
        int expected = 1; // the smallest value not accounted for yet
        int previous = 0;
        for (int value : nums) {
            if (value == previous) {
                // A third copy must not list the value again.
                if (duplicated.isEmpty() || duplicated.get(duplicated.size() - 1) != value) {
                    duplicated.add(value);
                }
                continue;
            }
            for (; expected < value; expected++) {
                missing.add(expected);
            }
            expected = value + 1;
            previous = value;
        }
        for (; expected <= nums.length; expected++) {
            missing.add(expected);
        }
        return List.of(missing, duplicated);
    }
}

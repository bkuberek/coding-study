import java.util.*;

public class Solution {
    public List<List<Integer>> findMissingAndDuplicates(int[] nums) {
        int n = nums.length;
        for (int i = 0; i < n; i++) {
            // Swap nums[i] to its home index nums[i] - 1 until the home already holds that
            // value. Comparing with the home, not with i, is what stops the loop on a repeat.
            while (nums[nums[i] - 1] != nums[i]) {
                int home = nums[i] - 1;
                int displaced = nums[home];
                nums[home] = nums[i];
                nums[i] = displaced;
            }
        }

        // Every value that occurs now sits at its home. A slot that holds another value is
        // either the home of a missing value or a spare copy of a value that is home
        // elsewhere. A negative sign on a home marks that its value has a spare copy.
        List<Integer> missing = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            if (Math.abs(nums[i]) == i + 1) {
                continue;
            }
            missing.add(i + 1);
            int spare = nums[i];
            nums[spare - 1] = -spare;
        }

        // The marks are read in index order, so the duplicates come out sorted too.
        List<Integer> duplicated = new ArrayList<>();
        for (int value = 1; value <= n; value++) {
            if (nums[value - 1] < 0) {
                duplicated.add(value);
            }
        }
        return List.of(missing, duplicated);
    }
}

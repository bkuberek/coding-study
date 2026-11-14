import java.util.*;

public class Solution {
    public int missingNumber(int[] nums) {
        int[] sorted = nums.clone();
        Arrays.sort(sorted);
        // In the sorted array, value i sits at index i until the gap.
        for (int index = 0; index < sorted.length; index++) {
            if (sorted[index] != index) {
                return index;
            }
        }
        return nums.length;
    }
}
